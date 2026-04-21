import dashscope
from dashscope import MultiModalConversation

import app.rag.config_data as config
from app.common.logger import logger
import base64
from typing import Any, Optional, Tuple


class VisionService:
    @staticmethod
    def _sniff_image_mime_from_b64(b64_data: str) -> Optional[str]:
        """
        该方法通过解码 base64 数据的前 512 字节，检查文件头魔数来识别图片真实格式：
            1. 检测 PNG、JPEG、GIF、WebP、AVIF、HEIF 等格式的特征字节
            2. 返回对应的 MIME 类型
            3. 无法识别则返回 None

        基于少量头部字节猜测图片真实 MIME（避免 dataURL 标注错误导致 SDK 拒绝）。

        """
        try:
            head = base64.b64decode(b64_data[:512], validate=False)
        except Exception:
            return None

        # PNG
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        # JPEG
        if head.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        # GIF
        if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
            return "image/gif"
        # WEBP: "RIFF....WEBP"
        if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WEBP":
            return "image/webp"
        # AVIF/HEIF: ISO BMFF ftyp box
        if b"ftypavif" in head[:32]:
            return "image/avif"
        if b"ftypheic" in head[:32] or b"ftypheif" in head[:32]:
            return "image/heif"
        return None

    @staticmethod
    def _normalize_data_uri(image_url: str) -> Tuple[str, Optional[str]]:
        """
        该方法用于修正图片 data URI 的 MIME 类型：
            非 data URI 直接返回
            解析 header 获取声明的 MIME 类型
            通过文件头字节检测真实 MIME 类型
            若两者不一致，修正为真实类型后返回
        若是 data URI，尽量修正 mime 与真实内容一致，返回 (normalized_data_uri, mime)。
        非 data URI 原样返回。
        """
        if not (isinstance(image_url, str) and image_url.startswith("data:image/")):
            return image_url, None

        try:
            header, b64_data = image_url.split(",", 1)
        except ValueError:
            return image_url, None

        # header: data:image/png;base64
        mime = None
        try:
            mime = header.split(";", 1)[0].split(":", 1)[1]
        except Exception:
            mime = None

        sniffed = VisionService._sniff_image_mime_from_b64(b64_data)
        if sniffed and sniffed != mime:
            # 修正 mime（比如前端标了 image/png，但实际是 AVIF）
            normalized = f"data:{sniffed};base64,{b64_data}"
            return normalized, sniffed

        return image_url, mime

    @staticmethod
    def recognize(image_url: str) -> str:
        """
        识别图片中的食材清单。
        该方法调用 DashScope 多模态 API 识别图片中的食材：
            1. 配置 API 密钥和端点
            2. 修正图片 MIME 类型
            3. 构建包含图片和提示词的消息
            4. 调用 API 并解析响应
            5. 返回识别结果或错误提示

        - 兼容前端 FileReader.readAsDataURL 生成的 data:image/...;base64,...
        - 也兼容 http(s) URL
        """
        dashscope.api_key = getattr(config, "DASHSCOPE_API_KEY", None)
        dashscope.base_http_api_url = getattr(
            config, "DASHSCOPE_SDK_BASE_URL", "https://dashscope.aliyuncs.com/api/v1"
        )

        prompt ="请识别图片中的所有食材，输出“食材清单”（用中文，逗号分隔即可），不要输出其它解释。"

        # DashScope 多模态 SDK 支持 data URI（data:image/...;base64,...）或 http(s) URL。
        # 不要把 data URI 的前缀剥掉，否则会被当成非法 URL/非法图片。
        image_payload, mime = VisionService._normalize_data_uri(image_url)
        if mime:
            logger.info(f"Vision 输入图片 MIME={mime}")

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": image_payload},
                    {"text": prompt},
                ],
            }
        ]

        try:
            response = MultiModalConversation.call(
                model=getattr(config, "vision_model_name", None),
                messages=messages,
            )
            # DashScope SDK 返回可能是 dict，也可能是带属性的对象；统一转 dict 处理
            if response is None:
                logger.error("Vision 识别失败：DashScope 返回 None")
                return "无法识别图片内容"

            if not isinstance(response, dict):
                # 尝试取常见属性
                try:
                    response = dict(response)  # type: ignore[arg-type]
                except Exception:
                    logger.error(f"Vision 返回非 dict：{type(response)} {response!r}")
                    return "无法识别图片内容"

            # 如果返回的是错误结构，尽量把原因记录出来
            if response.get("status_code") and int(response.get("status_code")) != 200:
                logger.error(f"Vision DashScope 非 200：{response}")
            if response.get("code") or response.get("message"):
                logger.error(f"Vision DashScope 错误：code={response.get('code')} message={response.get('message')}")

            output = response.get("output")
            if not isinstance(output, dict):
                logger.error(f"Vision DashScope output 异常：{output!r} full={response}")
                return "无法识别图片内容"

            choices = output.get("choices")
            if not (isinstance(choices, list) and choices):
                logger.error(f"Vision DashScope choices 异常：{choices!r} full={response}")
                return "无法识别图片内容"

            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = message.get("content", [])
            if not (isinstance(content, list) and content):
                logger.error(f"Vision DashScope content 异常：{content!r} full={response}")
                return "无法识别图片内容"

            text_out = ""
            if isinstance(content[0], dict):
                text_out = content[0].get("text", "") or ""
            return text_out.strip() or "无法识别图片内容"
        except Exception as e:
            # 打印异常与（如果有）响应体，便于排查参数/模型权限/图片格式问题
            logger.exception(f"Vision 识别失败：{e!r}")
            return "无法识别图片内容"


def recognize(image_url: str) -> str:
    return VisionService.recognize(image_url=image_url)