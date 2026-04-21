from pydantic import BaseModel, Field


# ---  数据模型 ---
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的文本信息")
    image_url: str = Field(default=None,description="用户上传的图片URL")
    thread_id: str = Field(..., description="对话线程ID，前端生成唯一ID（如UUID）")
