import json

from fastapi import APIRouter
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages import SystemMessage
from starlette.responses import StreamingResponse
from app.models.schemas import ChatRequest
from app.common.logger import logger
from app.rag.service import vision
from app.rag.rag import RagService
from app.rag.history.file_history_store import FileChatMessageHistory
from pathlib import Path
import app.rag.config_data as config

router = APIRouter(prefix="/api/chat", tags=["Chat"])
logger.info("app.chat")


@router.post("/stream", description="流式对话")
async def chat(request: ChatRequest):
    logger.info(f"开始处理请求: thread_id={request.thread_id}")

    # ===== 统一 message 结构 =====
    if request.image_url:
        request.message = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": request.image_url},
                    {"type": "text", "text": request.message or ""}
                ]
            }
        ]
    else:
        request.message = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": request.message}
                ]
            }
        ]

    return StreamingResponse(
        stream_agent_response(request.message, request.thread_id),
        media_type="text/plain; charset=utf-8"
    )


async def stream_agent_response(messages, thread_id):
    """流式生成智能体响应"""
    try:
        text = ""
        image_url = None
        image_mime = None

        # ===== 解析输入 ====
        # 遍历消息内容，解析文本和图片：
        # 1. 提取文本内容到 `text` 变量
        # 2. 提取图片 URL，区分 HTTP(S) 链接和 data URI
        # 3. 对于 data URI，解析出 MIME 类型
        # 4. 支持两种图片格式以兼容前端上传

        for m in messages:
            for item in m.get("content", []):
                if item.get("type") == "text":
                    text = item.get("text", "").strip()
                elif item.get("type") == "image":
                    url = item.get("url")
                    if not (url and isinstance(url, str)):
                        continue
                    # 支持 http(s) URL 以及 data URL（前端 FileReader.readAsDataURL）
                    if url.startswith("http"):
                        image_url = url
                        image_mime = None
                    elif url.startswith("data:image/"):
                        image_url = url
                        # data:image/png;base64,xxxx
                        try:
                            image_mime = url.split(";", 1)[0].split(":", 1)[1]
                        except Exception:
                            image_mime = None

        # =========================
        # 场景1：纯图片
        # =========================
        if image_url and not text:
            logger.info("[Router] 纯图片 → Vision + RAG")
            vision_text = vision.recognize(image_url)
            yield f"【识别到的食材】\n{vision_text}\n\n"
            final_input = f"""
                            【识别到的食材】
                            {vision_text}
                            【用户需求】
                            请根据以上食材，推荐 3-5 道最适合的家常菜，并给出每道菜的关键步骤与调味建议。
                            """
        # =========================
        # 场景2：图文
        # =========================
        elif image_url and text:
            logger.info("[Router] 图文 → Vision + RAG")
            vision_text = vision.recognize(image_url)
            yield f"【识别到的食材】\n{vision_text}\n\n"
            final_input = f"""
                            【识别到的食材】
                            {vision_text}             
                            【用户需求】
                            {text}
                            """

        # =========================
        # 场景3：纯文本
        # =========================
        else:
            logger.info("[Router] 纯文本 → RAG")
            final_input = text

        # =========================
        # RAG 调用（仅文本）
        # =========================
        final_input = str(final_input)
        session_config = {
            "configurable": {
                "session_id": thread_id,
            }
        }
        for chunk in RagService().chain.stream({"input": final_input, "request": {}}, session_config):
            yield chunk
    except Exception as e:
        logger.exception(f"请求处理失败：{e!r}")
        yield json.dumps({"error": f"处理失败: {str(e)}"}, ensure_ascii=False) + "\n"


@router.get("/messages", description="获取历史消息")
def get_chat_messages(thread_id: str):
    """获取历史消息"""
    logger.info(f"获取历史消息: thread_id={thread_id}")
    # 根据 thread_id 查询 历史消息
    try:
        storage_path = str(config.history_directory)
        history = FileChatMessageHistory(thread_id, storage_path)

        result = []
        for m in history.messages:
            if isinstance(m, HumanMessage):
                role = "user"
            elif isinstance(m, AIMessage):
                role = "assistant"
            elif isinstance(m, SystemMessage):
                # 前端不展示 system 消息
                continue
            else:
                role = "assistant"

            content = getattr(m, "content", "")
            if isinstance(content, list):
                # 兼容多模态 content 结构，只取文本部分
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(item.get("text", ""))
                content = "\n".join([p for p in parts if p])

            result.append({"role": role, "content": str(content)})

        return result
    except Exception as e:
        logger.exception(f"获取历史消息失败：{e!r}")
        return []


@router.get("/sessions", summary="获取所有历史会话列表（侧边栏用）")
def get_chat_sessions():
    """获取所有历史会话列表（侧边栏用）"""
    try:
        storage_dir = config.history_directory
        if not storage_dir.exists() or not storage_dir.is_dir():
            return []

        sessions = []
        for p in storage_dir.iterdir():
            if not p.is_file():
                continue

            thread_id = p.name
            try:
                # 取文件 mtime 作为会话时间
                timestamp_ms = int(p.stat().st_mtime * 1000)
            except Exception:
                timestamp_ms = 0

            title = "新会话"
            try:
                history = FileChatMessageHistory(thread_id, str(storage_dir))
                for m in history.messages:
                    if isinstance(m, HumanMessage):
                        content = getattr(m, "content", "")
                        if isinstance(content, list):
                            parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    parts.append(item.get("text", ""))
                            content = " ".join([x for x in parts if x])
                        content = str(content).strip()
                        if content:
                            title = content[:20] + ("..." if len(content) > 20 else "")
                        break
            except Exception:
                # 单个会话损坏/不可读则跳过标题提取，但仍返回基础信息
                pass

            sessions.append({"id": thread_id, "title": title, "timestamp": timestamp_ms})

        sessions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return sessions
    except Exception as e:
        logger.exception(f"获取会话列表失败：{e!r}")
        return []


@router.delete("/delete_by_thread_id", description="清空单条历史消息记录")
def clear_chat_messages(thread_id: str):
    """清空单条历史消息记录"""
    logger.info(f"清空历史消息: thread_id={thread_id}")
    try:
        storage_path = str(config.history_directory)
        history_file = Path(storage_path) / thread_id

        if history_file.exists():
            history_file.unlink()
            logger.info(f"成功删除历史消息文件: {thread_id}")
            return {"message": "历史消息已成功删除"}
        else:
            logger.warning(f"历史消息文件不存在: {thread_id}")
            return {"message": "历史消息文件不存在"}
    except Exception as e:
        logger.exception(f"删除历史消息失败：{e!r}")
        return {"message": f"删除失败: {str(e)}"}
