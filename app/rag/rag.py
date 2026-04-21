"""
rag服务
"""


import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import dashscope

from langchain_core.output_parsers import StrOutputParser

from app.rag.history.file_history_store import FileChatMessageHistory
from app.rag.service.vectore_stores import VectorStoreService
import app.rag.config_data as config
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.runnables import RunnableWithMessageHistory, RunnableLambda
from langchain_community.embeddings import DashScopeEmbeddings
import os

#
# 关键点：
# ChatTongyi 走的是 DashScope SDK（不是 OpenAI-compatible base_url）。
# 如果全局/环境把 DashScope SDK 的 base_http_api_url 指到了 /compatible-mode/v1，
# 会触发 400: "url error, please check url" 这类异常。
#
dashscope.api_key = getattr(config, "DASHSCOPE_API_KEY", None)
dashscope.base_http_api_url = getattr(config, "DASHSCOPE_SDK_BASE_URL", None)

os.environ["TAVILY_API_KEY"] = config.TAVILY_API_KEY
os.environ["TAVILY_API_KEY"] = config.TAVILY_API_KEY



def get_history(session_id):
    return FileChatMessageHistory(session_id, config.CHAT_HISTORY_PATH)

def print_model(prompt):
    print("=" * 20)
    print(prompt)
    print("=" * 20)
    return prompt

system_prompt = """
你是一名私人厨师。收到用户提供的食材照片或清单后，请按以下流程操作：
1.识别和评估食材：若用户提供照片，首先辨识所有可见食材。基于食材的外观状态，评估其新鲜度与可用量，整理出一份“当前可用食材清单”。
2.多维度评估与排序：从营养价值和制作难度两个维度对检索到的候选食谱进行量化打分，并根据得分综合排序。
3.结构化方案输出：把排序后的食谱整理为一份结构清晰的建议报告，帮助用户快速做出决策。
4.可以参考我提供的参考资料，简洁和专业的回答用户问题。参考资料:{context}。
"""

class RagService(object):
    def __init__(self):
        self.vector_store = VectorStoreService(
            embedding=DashScopeEmbeddings(model=config.embedding_model_name))

        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("system", "并且我提供用户的对话历史记录，如下："),
                MessagesPlaceholder("history"),
                ("user", "{input}")
            ]
        )

        self.model = ChatTongyi(model=config.chat_model_name)
        self.chain = self.__get_chain()

    def __get_chain(self):
        """
        获取问答链
        :return:
        """

        # 获取检索器
        retriever = self.vector_store.get_retriever()

        def format_docs(docs):
            if not docs:
                return "无参考资料"
            return "\n\n".join(doc.page_content for doc in docs)

        def safe_input(x):
            val = x.get("input", "")
            if not val or not isinstance(val, str) or val.strip() == "":
                return "推荐一些家常菜"
            return val

        def ensure_config(x):
            if not isinstance(x, dict):
                x = {"input": x}
            if "request" not in x:
                x["request"] = {}
            return x

        chain = (
                RunnableLambda(ensure_config)
                | {
                    "input": RunnableLambda(safe_input),
                    "history": RunnableLambda(lambda x: x.get("history", [])),
                    "context": RunnableLambda(lambda x: x["input"])
                               | retriever
                               | RunnableLambda(format_docs)
                }
                | self.prompt_template
                | self.model
                | StrOutputParser()
        )


        conversation_chain = RunnableWithMessageHistory(
            chain,
            get_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        return conversation_chain

        # return chain


if __name__ == '__main__':
    # Windows 控制台常见默认编码为 GBK，模型输出含 emoji/特殊字符时 print 会报错
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    service = RagService()

    # session id 配置（RunnableWithMessageHistory 必填）
    session_config = {
        "configurable": {
            "session_id": "user_001",
        }
    }

    res = service.chain.invoke(
        {"input": "我想吃牛肉了，帮我推荐菜的做法,要求是广东口味的"},
        session_config,
    )
    print(res)

    # res = service.chain.invoke({"input": "牛肉怎样做好吃？"}, session_config)
    # print(res)

    # chain.stream({
    #     "input": [
    #         {
    #             "role": "user",
    #             "content": [
    #                 {"type": "image", "url": "..."},
    #                 {"type": "text", "text": "帮我做菜"}
    #             ]
    #         }
    #     ]
    # })
