
from pydantic import BaseModel, Field


# ---  数据模型 ---
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的文本信息")
    image_url: str = Field(
        default="https://img.freepik.com/free-photo/arrangement-different-foods-organized-fridge_23-2149099882.jpg",# 方便测试，默认值
        description="用户上传的图片URL")
    thread_id: str = Field(..., description="对话线程ID，前端生成唯一ID（如UUID）")
