from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from pathlib import Path
import os

load_dotenv()

# 定义搜索工具，web搜索工具
web_search = TavilySearch(max_results=5, topic="general")

# 记忆管理
# 初始化checkpointer
BASE_DIR = Path(__file__).parent.parent
# 拼出数据库文件路径
DB_PATH = BASE_DIR / "db" / "personal_chief.db"
# 自动创建 resources 文件夹
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
# 使用同步的SqliteSaver
checkpointer = SqliteSaver(sqlite3.connect(DB_PATH, check_same_thread=False))
# ⾃动建表
checkpointer.setup()

# 系统提示词
system_prompt = """
你是一名私人厨师。收到用户提供的食材照片或清单后，请按以下流程操作：
1.识别和评估食材：若用户提供照片，首先辨识所有可见食材。基于食材的外观状态，评估其新鲜度与可用量，整理出一份“当前可用食材清单”。
2.智能食谱检索：优先调用 web_search 工具，以“可用食材清单”为核心关键词，查找可行菜谱。
3.多维度评估与排序：从营养价值和制作难度两个维度对检索到的候选食谱进行量化打分，并根据得分综合排序。
4.结构化方案输出：把排序后的食谱整理为一份结构清晰的建议报告，帮助用户快速做出决策。

请严格按照流程，优先调用 web_search 工具搜索食谱，再搜索不到的情况下才能自己发挥。
"""

# 1.定义模型
multimodal_mode = init_chat_model(
    model="qwen3-omni-flash",  # 模型名称:qwen3.5-plus，这是一个多模态模型，支持图片、文本、音频、视频
    model_provider="openai",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 2.创建智能体
agent = create_agent(
    model=multimodal_mode,
    system_prompt=system_prompt,
    tools=[web_search],
    checkpointer=checkpointer
)
