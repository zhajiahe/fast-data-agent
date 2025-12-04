"""
对话 API 路由

提供对话消息接口，使用 LangChain 消息格式
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.models.chat_message import ChatMessage
from app.schemas.chat_message import ChatMessageCreate, ChatMessageResponse
from app.services.analysis_session import AnalysisSessionService
from app.services.chat import ChatService

router = APIRouter(prefix="/sessions/{session_id}", tags=["chat"])


# ==================== 消息序列化 ====================


def _serialize_message(message: BaseMessage) -> dict[str, Any]:
    """将 LangChain 消息序列化为 JSON 可传输格式"""
    if isinstance(message, HumanMessage):
        return {
            "type": "human",
            "content": message.content,
            "id": getattr(message, "id", None),
        }
    elif isinstance(message, AIMessage):
        result: dict[str, Any] = {
            "type": "ai",
            "content": message.content,
            "id": getattr(message, "id", None),
        }
        if message.tool_calls:
            result["tool_calls"] = [
                {"id": tc.get("id"), "name": tc.get("name"), "args": tc.get("args")}
                for tc in message.tool_calls
            ]
        return result
    elif isinstance(message, ToolMessage):
        return {
            "type": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id,
            "name": getattr(message, "name", None),
        }
    else:
        return {
            "type": getattr(message, "type", "unknown"),
            "content": str(message.content) if hasattr(message, "content") else str(message),
        }


def _serialize_chunk(chunk: dict[str, Any] | tuple[Any, Any]) -> dict[str, Any]:
    """序列化流式 chunk
    
    当 stream_mode="messages" 时，chunk 是 (message, metadata) 的 tuple
    当 stream_mode="values" 或 "updates" 时，chunk 是 dict
    """
    # 处理 tuple 格式 (message, metadata)
    if isinstance(chunk, tuple):
        message, metadata = chunk
        return {
            "content": str(message.content) if hasattr(message, "content") else "",
            "type": getattr(message, "type", "ai"),
            "id": getattr(message, "id", None),
        }
    
    # 处理 dict 格式
    result: dict[str, Any] = {}

    if "messages" in chunk:
        messages = chunk["messages"]
        if isinstance(messages, list):
            result["messages"] = [_serialize_message(m) for m in messages]
        else:
            result["messages"] = [_serialize_message(messages)]

    for key, value in chunk.items():
        if key != "messages":
            result[key] = value

    return result


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
        async for chunk in chat_service.chat(content, session, stream_mode="messages"):
            # 检查是否是 dict 且包含 error
            if isinstance(chunk, dict) and "error" in chunk:
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                continue

            serialized = _serialize_chunk(chunk)
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
