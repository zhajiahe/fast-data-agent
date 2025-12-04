"""
对话 API 路由

提供对话消息接口，使用 LangChain 消息格式
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, ToolMessageChunk

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.models.message import ChatMessage
from app.schemas.message import ChatMessageCreate, ChatMessageResponse
from app.services.session import AnalysisSessionService
from app.services.chat import ChatService

router = APIRouter(prefix="/sessions/{session_id}", tags=["chat"])


# ==================== 消息序列化 ====================


def _serialize_message(message: Any) -> dict[str, Any]:
    """序列化单个消息对象"""
    from langchain_core.messages import AIMessage, ToolMessage

    result: dict[str, Any] = {
        "content": str(message.content) if hasattr(message, "content") else "",
        "type": getattr(message, "type", "unknown"),
        "id": getattr(message, "id", None),
    }

    # AIMessage 可能包含 tool_calls
    if isinstance(message, AIMessage) and message.tool_calls:
        result["tool_calls"] = message.tool_calls

    # ToolMessage 包含 tool_call_id 和可能的 artifact
    if isinstance(message, ToolMessage):
        result["tool_call_id"] = getattr(message, "tool_call_id", None)
        result["name"] = getattr(message, "name", None)
        artifact = getattr(message, "artifact", None)
        if artifact:
            result["artifact"] = artifact

    return result


def _serialize_chunk(chunk: dict[str, Any] | tuple[Any, Any]) -> dict[str, Any]:
    """序列化流式 chunk

    stream_mode=["values", "updates", "messages"] 时：
    - tuple: "messages" 模式的 (message/message_chunk, metadata)
    - dict with "mode": "updates": 状态更新（工具调用和结果）
    - dict with "error": 错误信息
    """
    from langchain_core.messages import ToolMessage

    # 处理 tuple 格式 (message/message_chunk, metadata) - messages 模式
    if isinstance(chunk, tuple):
        message, _metadata = chunk
        result: dict[str, Any] = {
            "mode": "messages",
            "content": str(message.content) if hasattr(message, "content") else "",
            "type": getattr(message, "type", "ai"),
            "id": getattr(message, "id", None),
        }

        # AIMessageChunk 可能包含 tool_calls
        if isinstance(message, AIMessageChunk) and message.tool_calls:
            result["tool_calls"] = message.tool_calls

        # ToolMessage 或 ToolMessageChunk 包含 tool_call_id
        if isinstance(message, (ToolMessage, ToolMessageChunk)):
            result["tool_call_id"] = getattr(message, "tool_call_id", None)
            result["name"] = getattr(message, "name", None)
            artifact = getattr(message, "artifact", None)
            if artifact:
                result["artifact"] = artifact

        return result

    # 处理 dict 格式
    if isinstance(chunk, dict):
        # updates 模式：状态更新（包含工具调用和结果）
        if chunk.get("mode") == "updates":
            data = chunk.get("data", {})
            result = {"mode": "updates", "node": None, "messages": []}

            # 提取节点名称和消息
            for node_name, node_data in data.items():
                result["node"] = node_name
                if isinstance(node_data, dict) and "messages" in node_data:
                    messages = node_data["messages"]
                    if isinstance(messages, list):
                        result["messages"] = [_serialize_message(m) for m in messages]
                    else:
                        result["messages"] = [_serialize_message(messages)]
            return result

        # error 或其他 dict 格式
        return chunk

    return {"error": "Unknown chunk format"}


def _chat_message_to_response(msg: ChatMessage) -> ChatMessageResponse:
    """将数据库消息转换为 API 响应格式"""
    return ChatMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        message_type=msg.message_type,
        content=msg.content,
        message_id=msg.message_id,
        name=msg.name,
        tool_calls=msg.tool_calls,
        tool_call_id=msg.tool_call_id,
        usage_metadata=msg.usage_metadata,
        create_time=msg.create_time,
    )


# ==================== SSE 流式响应 ====================


async def _stream_chat_response(
    chat_service: ChatService,
    content: str,
    session_id: int,
    user_id: int,
    db: Any,
) -> AsyncGenerator[str, None]:
    """生成 SSE 流式响应"""
    session_service = AnalysisSessionService(db)
    session = await session_service.get_session(session_id, user_id)

    try:
        async for chunk in chat_service.chat(content, session):
            # 检查是否是 dict 且包含 error
            if isinstance(chunk, dict) and "error" in chunk:
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                continue

            serialized = _serialize_chunk(chunk)
            
            # 过滤空内容的消息（只有 content 且为空/空白的 messages 模式）
            if serialized.get("mode") == "messages":
                content = serialized.get("content", "")
                tool_calls = serialized.get("tool_calls")
                tool_call_id = serialized.get("tool_call_id")
                # 跳过既没有内容也没有工具调用的消息
                if not content and not tool_calls and not tool_call_id:
                    continue
            
            yield f"data: {json.dumps(serialized, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        error = {"error": {"message": str(e), "type": type(e).__name__}}
        yield f"data: {json.dumps(error, ensure_ascii=False)}\n\n"


# ==================== API 端点 ====================


@router.post("/chat", response_class=StreamingResponse)
async def chat(
    session_id: int,
    data: ChatMessageCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    发送消息并获取 AI 响应（SSE 流式）

    使用 LangChain 消息格式：
    - `human`: 用户消息
    - `ai`: AI 助手消息，可能包含 `tool_calls`
    - `tool`: 工具执行结果

    流结束时发送 `[DONE]`
    """
    session_service = AnalysisSessionService(db)
    await session_service.get_session(session_id, current_user.id)

    chat_service = ChatService(db)

    return StreamingResponse(
        _stream_chat_response(chat_service, data.content, session_id, current_user.id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/messages", response_model=BaseResponse[PageResponse[ChatMessageResponse]])
async def get_messages(
    session_id: int,
    current_user: CurrentUser,
    db: DBSession,
    page_query: BasePageQuery = Depends(),
):
    """
    获取会话的历史消息（分页）

    返回消息列表，按创建时间升序排列
    """
    # 验证会话权限
    session_service = AnalysisSessionService(db)
    await session_service.get_session(session_id, current_user.id)

    # 获取历史消息
    chat_service = ChatService(db)
    skip = (page_query.page_num - 1) * page_query.page_size
    messages, total = await chat_service.get_history(
        session_id,
        skip=skip,
        limit=page_query.page_size,
    )

    # 转换为响应格式
    items = [_chat_message_to_response(msg) for msg in messages]

    return BaseResponse(
        success=True,
        code=200,
        msg="获取消息列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=total,
            items=items,
        ),
    )
