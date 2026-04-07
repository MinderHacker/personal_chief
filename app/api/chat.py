import json
import time

from fastapi import APIRouter
from langchain_core.messages import HumanMessage, AIMessage
from starlette.responses import StreamingResponse
from app.models.schemas import ChatRequest
from app.agent.personal_chief import agent, checkpointer
from app.common.logger import logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])
logger.info("app.chat")


@router.post("/stream", description="流式对话")
async def chat(request: ChatRequest):
    """调用agent搜索食谱"""
    logger.info(f"开始处理请求: thread_id={request.thread_id}")
    # 判断是否有图片，封装不同格式的消息
    if not request.image_url or request.image_url == "":
        request.message = [
            {"role": "user",
             "content": [
                 {"type": "text", "text": request.message}
             ]}
        ]
    else:
        # 有图片时使用多模态格式
        request.message = [
            {"role": "user",
             "content": [
                 {"type": "image", "url": request.image_url},
                 {"type": "text", "text": request.message}
             ]}
        ]
    return StreamingResponse(stream_agent_response(request), media_type="text/plain; charset=utf-8")


async def stream_agent_response(request: ChatRequest):
    """流式生成智能体响应"""
    try:
        # 流式调用Agent
        stream_response = agent.stream(
            {"messages": request.message},
            stream_mode="messages",
            config={"configurable": {"thread_id": request.thread_id}}
        )
        for chunk in stream_response:
            msg= chunk[0]
            # 核心过滤逻辑：只保留最终给用户的AI回答
            # 1. 必须是 AIMessage 类型（排除工具返回、用户消息等）
            # 2. 不是工具调用消息（排除Agent发的工具请求）
            # 3. 有实际内容（排除空消息）
            if (
                    isinstance(msg, AIMessage)
                    and not msg.tool_calls  # 排除工具调用指令
                    and msg.content.strip()  # 排除空内容
            ):
                yield msg.content
            # if chunk and hasattr(chunk[0], 'content'):
            #     content = chunk[0].content
            #     if content:
            #         # 直接返回文字，不包JSON！！
            #         yield content

    except Exception as e:
        logger.error(f"请求处理失败：{str(e)}")
        yield json.dumps({"error": f"信息检索失败，请检查输入内容: {str(e)}"}, ensure_ascii=False) + "\n"


@router.get("/messages", description="获取历史消息")
def get_chat_messages(thread_id: str):
    """获取历史消息"""
    logger.info(f"获取历史消息: thread_id={thread_id}")
    # 根据 thread_id 查询 checkpoint
    checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})

    # 如果不存在，返回空列表
    if not checkpoint:
        return []

    # 安全获取 messages
    channel_values = checkpoint.get("channel_values")
    if not channel_values:
        return []

    messages = channel_values.get("messages", [])
    if not messages:
        return []

    # 转换消息格式
    result = []
    for msg in messages:
        if not msg.content:
            continue
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            result.append({"role": "assistant", "content": msg.content})
    return result


@router.delete("/clear",description="清空历史消息")
def clear_chat_messages(thread_id: str):
    """清空历史消息"""
    logger.info(f"清空历史消息: thread_id={thread_id}")
    checkpointer.delete_thread(thread_id)


@router.get("/sessions", summary="获取所有历史会话列表（侧边栏用）")
def get_chat_sessions():
    try:
        conn = checkpointer.conn
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT DISTINCT thread_id
                       FROM checkpoints
                       ORDER BY checkpoint_id DESC
                       """)

        rows = cursor.fetchall()
        sessions = []

        for (thread_id,) in rows:
            try:
                checkpoint = checkpointer.get({"configurable": {"thread_id": thread_id}})
                if not checkpoint:
                    continue

                # 取第一条消息做标题
                channel_values = checkpoint.get("channel_values", {})
                messages = channel_values.get("messages", [])

                title = "新对话"
                if messages:
                    first_msg = messages[0]
                    if hasattr(first_msg, "content"):
                        title = first_msg.content[:30]
                    elif isinstance(first_msg, dict):
                        title = first_msg.get("content", "新对话")[:30]

                sessions.append({
                    "thread_id": thread_id,
                    "title": title
                })
            except:
                continue
        return sessions
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}", exc_info=True)
        return []