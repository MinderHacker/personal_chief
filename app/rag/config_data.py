"""
配置文件
"""

from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

# md5文件
project_root = Path(__file__).resolve().parents[2]
md5_path = str(project_root / "upload" / "md5.txt")

# aliyun
# 兼容地址用于 OpenAI-compatible 客户端（例如 base_url=".../compatible-mode/v1"）
DASHSCOPE_SDK_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
DASHSCOPE_COMPATIBLE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# Chroma
collection_name = "rag"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
persist_directory = str(PROJECT_ROOT / "app" / "data" / "chroma_db")
history_directory = str(PROJECT_ROOT / "app" / "data" / "chat_history")

# spliter
chunk_size = 500
chunk_overlap = 100
separators = ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
max_split_char_number = 500  # 文本分割的阈值

# 向量检索
similarity_threshold = 1  # 检索返回匹配的文档数量

# 文本对话模型（RAG 生成用）：建议使用纯文本模型
chat_model_name = "qwen-plus"

# 多模态识别模型（图片识别用）
vision_model_name = "qwen3-omni-flash"
# 文本切分模型
embedding_model_name = "text-embedding-v3"

session_config = {
    "configurable": {
        "session_id": "user_001",
    }
}

# 聊天历史记录存储路径（统一用项目根目录）
CHAT_HISTORY_PATH = str(PROJECT_ROOT / "app" / "data" / "chat_history")

# 从.env读取敏感配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
