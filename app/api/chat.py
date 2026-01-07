"""
对话 API 路由

提供对话消息接口，兼容 Vercel AI SDK Data Stream Protocol

SSE 数据流协议 (兼容 @ai-sdk/react useChat):
- start: 消息开始
- text-start/text-delta/text-end: 文本流
- tool-input-start/tool-input-available: 工具调用
- tool-output-available: 工具结果
- finish-step/finish: 步骤/消息结束
- error: 错误
- [DONE]: 流结束

参考: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, ToolMessageChunk
from loguru import logger

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.models.message import ChatMessage
from app.repositories.message import ChatMessageRepository
from app.schemas.message import (
    BatchMessagesRequest,
    BatchMessagesResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    SessionMessages,
)
from app.services.chat import ChatService
from app.services.session import AnalysisSessionService

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


# ==================== Vercel AI SDK Data Stream Protocol ====================


def _sse_data(data: dict[str, Any] | str) -> str:
    """格式化 SSE data 行

    Vercel AI SDK 使用纯 data: 格式，不使用 event: 字段
    """
    if isinstance(data, str):
        return f"data: {data}\n\n"
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class VercelStreamBuilder:
    """Vercel AI SDK 兼容的流构建器

    实现 Data Stream Protocol:
    https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
    """

    def __init__(self) -> None:
        self.message_id = f"msg_{uuid.uuid4().hex}"
        self.text_id = f"text_{uuid.uuid4().hex}"
        self.text_started = False
        self.current_tool_calls: dict[str, dict[str, Any]] = {}  # toolCallId -> tool info

    def message_start(self) -> str:
        """消息开始"""
        return _sse_data({"type": "start", "messageId": self.message_id})

    def text_start(self) -> str:
        """文本块开始"""
        self.text_started = True
        return _sse_data({"type": "text-start", "id": self.text_id})

    def text_delta(self, content: str) -> str:
        """文本增量"""
        return _sse_data({"type": "text-delta", "id": self.text_id, "delta": content})

    def text_end(self) -> str:
        """文本块结束"""
        self.text_started = False
        current_text_id = self.text_id
        # 生成新的 text_id 用于下一个文本块
        self.text_id = f"text_{uuid.uuid4().hex}"
        return _sse_data({"type": "text-end", "id": current_text_id})

    def tool_input_start(self, tool_call_id: str, tool_name: str) -> str:
        """工具输入开始"""
        self.current_tool_calls[tool_call_id] = {"toolName": tool_name, "input": {}}
        return _sse_data(
            {
                "type": "tool-input-start",
                "toolCallId": tool_call_id,
                "toolName": tool_name,
            }
        )

    def tool_input_available(self, tool_call_id: str, tool_name: str, args: dict[str, Any]) -> str:
        """工具输入完成"""
        return _sse_data(
            {
                "type": "tool-input-available",
                "toolCallId": tool_call_id,
                "toolName": tool_name,
                "input": args,
            }
        )

    def tool_output_available(
        self,
        tool_call_id: str,
        output: Any,
        artifact: dict[str, Any] | None = None,
        tool_name: str | None = None,
    ) -> str:
        """工具输出完成"""
        result: dict[str, Any] = {
            "type": "tool-output-available",
            "toolCallId": tool_call_id,
            "output": output,
        }
        if tool_name:
            result["toolName"] = tool_name
        # 如果有 artifact（如图表数据），作为额外数据传递
        if artifact:
            result["artifact"] = artifact
        return _sse_data(result)

    def start_step(self) -> str:
        """步骤开始"""
        return _sse_data({"type": "start-step"})

    def finish_step(self) -> str:
        """步骤结束"""
        return _sse_data({"type": "finish-step"})

    def finish(self) -> str:
        """消息结束"""
        return _sse_data({"type": "finish"})

    def error(self, message: str) -> str:
        """错误"""
        return _sse_data({"type": "error", "errorText": message})

    @staticmethod
    def done() -> str:
        """流结束标记"""
        return _sse_data("[DONE]")


def _chat_message_to_response(msg: ChatMessage) -> ChatMessageResponse:
    """将数据库消息转换为 API 响应格式"""
    return ChatMessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        seq=msg.seq,
        message_type=msg.message_type,
        content=msg.content,
        message_id=msg.message_id,
        name=msg.name,
        tool_calls=msg.tool_calls,
        tool_call_id=msg.tool_call_id,
        artifact=msg.artifact,  # 工具产出物（图表、表格等）
        usage_metadata=msg.usage_metadata,
        create_time=msg.create_time,
    )


# ==================== 错误信息脱敏 ====================

# 敏感关键词列表，用于识别需要脱敏的错误信息
_SENSITIVE_KEYWORDS = frozenset(
    [
        "password",
        "secret",
        "key",
        "token",
        "credential",
        "api_key",
        "access_key",
        "private",
        "auth",
        "/home/",
        "/root/",
        "/app/",
        "/var/",
        "traceback",
        'file "',
        "line ",
    ]
)


def _sanitize_error_message(error_msg: str) -> str:
    """
    脱敏错误信息，移除可能泄露敏感信息的内容

    Args:
        error_msg: 原始错误信息

    Returns:
        脱敏后的错误信息
    """
    error_lower = error_msg.lower()

    # 检查是否包含敏感关键词
    for keyword in _SENSITIVE_KEYWORDS:
        if keyword in error_lower:
            # 记录原始错误到日志（供调试）
            logger.warning(f"Sanitized error message containing '{keyword}': {error_msg[:200]}")
            return "处理请求时发生内部错误，请稍后重试"

    # 限制错误信息长度，避免泄露过多细节
    max_length = 200
    if len(error_msg) > max_length:
        return error_msg[:max_length] + "..."

    return error_msg


# ==================== SSE 流式响应 ====================


async def _stream_chat_response(
    content: str,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request | None = None,
) -> AsyncGenerator[str, None]:
    """生成兼容 Vercel AI SDK 的 SSE 流式响应

    Data Stream Protocol:
    - start: 消息开始
    - text-start/text-delta/text-end: 文本流
    - tool-input-start/tool-input-available: 工具调用
    - tool-output-available: 工具结果
    - finish-step/finish: 步骤/消息结束
    - error: 错误
    - [DONE]: 流结束

    流模式分工：
    - messages 模式：处理 LLM token 流（文本增量）
    - updates 模式：仅处理工具调用结果（避免与 messages 模式重复）

    客户端断开检测：
    - 使用 request.is_disconnected() 检测客户端是否断开
    - 断开后停止处理并记录日志

    数据库事务策略：
    - 使用短生命周期的数据库会话，避免长时间占用连接
    - 每个数据库操作使用独立事务
    """
    from langchain_core.messages import ToolMessage

    from app.core.database import AsyncSessionLocal

    # 使用短生命周期的数据库会话获取初始数据
    async with AsyncSessionLocal() as db:
        session_service = AnalysisSessionService(db)
        session, raw_data_list = await session_service.get_session_with_raw_data(session_id, user_id)
        await db.commit()  # 提交读取事务
    # 数据库会话在这里已关闭，后续操作使用会话工厂

    # 创建 ChatService，使用会话工厂模式（每个数据库操作使用独立的短事务）
    chat_service = ChatService(db_factory=AsyncSessionLocal)

    builder = VercelStreamBuilder()
    sent_tool_outputs: set[str] = set()  # 跟踪已发送的工具输出，避免重复
    sent_tool_inputs: set[str] = set()  # 跟踪已发送的工具输入，避免重复
    is_disconnected = False

    async def check_disconnect() -> bool:
        """检查客户端是否断开连接"""
        if request is not None:
            return await request.is_disconnected()
        return False

    try:
        yield builder.message_start()
        yield builder.start_step()

        async for chunk in chat_service.chat(content, session, raw_data_list):
            # 定期检查客户端是否断开（每处理一个 chunk 检查一次）
            if await check_disconnect():
                is_disconnected = True
                logger.info(f"Client disconnected during chat stream: session_id={session_id}")
                break

            # 错误处理
            if isinstance(chunk, dict) and "error" in chunk:
                error_info = chunk.get("error", {})
                error_msg = (
                    error_info.get("message", "Unknown error") if isinstance(error_info, dict) else str(error_info)
                )
                # 脱敏错误信息
                safe_error_msg = _sanitize_error_message(error_msg)
                yield builder.error(safe_error_msg)
                continue

            # messages 模式：处理 LLM token 流
            if isinstance(chunk, tuple):
                message, _metadata = chunk

                # ToolMessage -> 工具结果（通过 messages 模式收到的工具结果）
                if isinstance(message, (ToolMessage, ToolMessageChunk)):
                    tool_call_id = getattr(message, "tool_call_id", None) or f"call_{uuid.uuid4().hex[:8]}"
                    if tool_call_id in sent_tool_outputs:
                        continue
                    sent_tool_outputs.add(tool_call_id)

                    tool_name = getattr(message, "name", None)
                    content_str = str(message.content) if hasattr(message, "content") else ""
                    artifact = getattr(message, "artifact", None)

                    try:
                        output = json.loads(content_str) if content_str else {}
                    except json.JSONDecodeError:
                        output = {"result": content_str}

                    yield builder.tool_output_available(tool_call_id, output, artifact, tool_name)
                    continue

                # AIMessageChunk -> 文本流 + 工具调用
                if isinstance(message, AIMessageChunk):
                    # 1. 文本内容
                    text_content = str(message.content) if message.content else ""
                    if text_content:
                        if not builder.text_started:
                            yield builder.text_start()
                        yield builder.text_delta(text_content)

                    # 2. 工具调用
                    if message.tool_calls:
                        if builder.text_started:
                            yield builder.text_end()

                        for tool_call in message.tool_calls:
                            tool_call_id = tool_call.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                            if tool_call_id in sent_tool_inputs:
                                continue
                            sent_tool_inputs.add(tool_call_id)

                            tool_name = tool_call.get("name") or "unknown"
                            tool_args = tool_call.get("args", {})
                            # 调试日志：查看原始 tool_call 数据
                            logger.debug(
                                f"Tool call received: id={tool_call_id}, name={tool_name}, args={tool_args}, raw={tool_call}"
                            )
                            yield builder.tool_input_start(tool_call_id, tool_name)
                            yield builder.tool_input_available(tool_call_id, tool_name, tool_args)
                    continue

                # 其他消息类型
                text_content = str(message.content) if hasattr(message, "content") and message.content else ""
                if text_content:
                    if not builder.text_started:
                        yield builder.text_start()
                    yield builder.text_delta(text_content)
                continue

            # updates 模式：仅处理工具结果（文本内容已通过 messages 模式处理，不再重复）
            if isinstance(chunk, dict) and chunk.get("mode") == "updates":
                data = chunk.get("data", {})

                for _node_name, node_data in data.items():
                    if isinstance(node_data, dict) and "messages" in node_data:
                        messages = node_data["messages"]
                        if not isinstance(messages, list):
                            messages = [messages]

                        for msg in messages:
                            serialized = _serialize_message(msg)

                            # 只处理工具结果（ToolMessage）
                            if serialized.get("tool_call_id"):
                                tool_call_id = serialized["tool_call_id"]
                                if tool_call_id in sent_tool_outputs:
                                    continue
                                sent_tool_outputs.add(tool_call_id)

                                tool_name = serialized.get("name")
                                content_str = serialized.get("content", "")
                                artifact = serialized.get("artifact")

                                try:
                                    output = json.loads(content_str) if content_str else {}
                                except json.JSONDecodeError:
                                    output = {"result": content_str}

                                yield builder.tool_output_available(tool_call_id, output, artifact, tool_name)

        # 如果客户端断开，不发送结束消息
        if is_disconnected:
            return

        # 结束文本块
        if builder.text_started:
            yield builder.text_end()

        yield builder.finish_step()
        yield builder.finish()

    except asyncio.CancelledError:
        # 任务被取消（通常是因为客户端断开）
        logger.info(f"Chat stream cancelled: session_id={session_id}")
        return

    except Exception as e:
        # 脱敏错误信息
        error_msg = str(e)
        safe_error_msg = _sanitize_error_message(error_msg)
        # 记录完整错误到日志
        logger.exception(f"Chat stream error: session_id={session_id}")
        yield builder.error(safe_error_msg)

    finally:
        if not is_disconnected:
            yield builder.done()


# ==================== API 端点 ====================


@router.post("/chat", response_class=StreamingResponse)
async def chat(
    request: Request,
    session_id: uuid.UUID,
    data: ChatMessageCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    发送消息并获取 AI 响应（SSE 流式）

    兼容 Vercel AI SDK useChat hook，使用 Data Stream Protocol。

    ## 流协议

    使用 SSE `data:` 格式，通过 JSON 的 `type` 字段区分事件类型。

    ### 消息开始
    ```
    data: {"type":"start","messageId":"msg_xxx"}
    ```

    ### 文本流 (start/delta/end 模式)
    ```
    data: {"type":"text-start","id":"text_xxx"}
    data: {"type":"text-delta","id":"text_xxx","delta":"你好"}
    data: {"type":"text-end","id":"text_xxx"}
    ```

    ### 工具调用
    ```
    data: {"type":"tool-input-start","toolCallId":"call_xxx","toolName":"execute_sql"}
    data: {"type":"tool-input-available","toolCallId":"call_xxx","toolName":"execute_sql","input":{...}}
    ```

    ### 工具结果
    ```
    data: {"type":"tool-output-available","toolCallId":"call_xxx","output":{...},"artifact":{...}}
    ```

    ### 步骤控制
    ```
    data: {"type":"start-step"}
    data: {"type":"finish-step"}
    data: {"type":"finish"}
    ```

    ### 错误
    ```
    data: {"type":"error","errorText":"..."}
    ```

    ### 流结束
    ```
    data: [DONE]
    ```

    参考: https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol

    ## 客户端断开处理

    服务端会检测客户端断开，并优雅地停止流处理，避免资源浪费。

    数据库事务策略：
    - 验证会话权限后立即释放数据库连接
    - 流式响应中使用独立的短生命周期事务
    - 避免长时间占用数据库连接池
    """
    # 验证会话权限（使用请求级别的数据库会话）
    session_service = AnalysisSessionService(db)
    await session_service.get_session(session_id, current_user.id)
    # 请求级别的 db 会话在这里不再需要，流式响应会使用独立的会话工厂

    return StreamingResponse(
        _stream_chat_response(data.content, session_id, current_user.id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            # Vercel AI SDK Data Stream Protocol header
            "x-vercel-ai-ui-message-stream": "v1",
        },
    )


@router.get("/messages", response_model=BaseResponse[PageResponse[ChatMessageResponse]])
async def get_messages(
    session_id: uuid.UUID,
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


@router.delete("/messages", response_model=BaseResponse[int])
async def clear_messages(
    session_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """清空会话的所有消息"""
    # 验证会话权限
    session_service = AnalysisSessionService(db)
    await session_service.get_session(session_id, current_user.id)

    # 清空消息
    repo = ChatMessageRepository(db)
    count = await repo.clear_by_session(session_id)
    await db.commit()

    return BaseResponse(
        success=True,
        code=200,
        msg=f"已清空 {count} 条消息",
        data=count,
    )


# ==================== 批量消息 API ====================

# 注意：这是一个独立的路由，不在 /sessions/{session_id} 下
batch_router = APIRouter(prefix="/messages", tags=["messages"])


@batch_router.post("/batch", response_model=BaseResponse[BatchMessagesResponse])
async def get_messages_batch(
    request: BatchMessagesRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    批量获取多个会话的消息

    用于一次性获取多个会话的消息，避免 N+1 查询问题。
    比如图表工作台需要获取所有会话的消息来提取图表。

    **性能优化**：
    - 单次数据库查询获取所有消息
    - 最多支持 100 个会话
    - 每个会话最多返回 page_size 条消息

    **权限**：
    - 仅返回属于当前用户的会话消息
    - 不属于当前用户的会话会被静默忽略
    """
    from app.repositories.session import AnalysisSessionRepository

    session_repo = AnalysisSessionRepository(db)
    message_repo = ChatMessageRepository(db)

    # 验证会话权限：只获取属于当前用户的会话
    valid_sessions = await session_repo.get_by_ids_and_user(request.session_ids, current_user.id)
    valid_session_ids = [s.id for s in valid_sessions]

    if not valid_session_ids:
        return BaseResponse(
            success=True,
            code=200,
            msg="获取消息成功",
            data=BatchMessagesResponse(items=[]),
        )

    # 批量获取消息
    messages_by_session = await message_repo.get_by_sessions_batch(
        valid_session_ids, limit_per_session=request.page_size
    )

    # 批量获取消息总数
    counts_by_session = await message_repo.count_by_sessions_batch(valid_session_ids)

    # 构建响应
    items = []
    for session_id in valid_session_ids:
        messages = messages_by_session.get(session_id, [])
        total = counts_by_session.get(session_id, 0)
        items.append(
            SessionMessages(
                session_id=session_id,
                messages=[_chat_message_to_response(msg) for msg in messages],
                total=total,
            )
        )

    return BaseResponse(
        success=True,
        code=200,
        msg="获取消息成功",
        data=BatchMessagesResponse(items=items),
    )
