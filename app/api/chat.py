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

import json
import uuid
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
        # 生成新的 text_id 用于下一个文本块
        self.text_id = f"text_{uuid.uuid4().hex}"
        return _sse_data({"type": "text-end", "id": self.text_id})

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
    ) -> str:
        """工具输出完成"""
        result: dict[str, Any] = {
            "type": "tool-output-available",
            "toolCallId": tool_call_id,
            "output": output,
        }
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


# ==================== SSE 流式响应 ====================


async def _stream_chat_response(
    chat_service: ChatService,
    content: str,
    session_id: int,
    user_id: int,
    db: Any,
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
    """
    from langchain_core.messages import ToolMessage

    session_service = AnalysisSessionService(db)
    session = await session_service.get_session(session_id, user_id)

    builder = VercelStreamBuilder()

    try:
        # 发送消息开始
        yield builder.message_start()
        yield builder.start_step()

        async for chunk in chat_service.chat(content, session):
            # 检查是否是 dict 且包含 error
            if isinstance(chunk, dict) and "error" in chunk:
                error_info = chunk.get("error", {})
                error_msg = (
                    error_info.get("message", "Unknown error") if isinstance(error_info, dict) else str(error_info)
                )
                yield builder.error(error_msg)
                continue

            # 处理 tuple 格式 (message/message_chunk, metadata) - messages 模式
            if isinstance(chunk, tuple):
                message, _metadata = chunk

                # AIMessageChunk 包含 tool_calls -> tool 调用
                if isinstance(message, AIMessageChunk) and message.tool_calls:
                    # 如果有文本在进行中，先结束它
                    if builder.text_started:
                        yield builder.text_end()

                    for tool_call in message.tool_calls:
                        tool_call_id = tool_call.get("id", f"call_{uuid.uuid4().hex[:8]}")
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("args", {})

                        # 发送工具调用开始和完成
                        yield builder.tool_input_start(tool_call_id, tool_name)
                        yield builder.tool_input_available(tool_call_id, tool_name, tool_args)
                    continue

                # ToolMessage 或 ToolMessageChunk -> 工具结果
                if isinstance(message, (ToolMessage, ToolMessageChunk)):
                    tool_call_id = getattr(message, "tool_call_id", None) or f"call_{uuid.uuid4().hex[:8]}"
                    content_str = str(message.content) if hasattr(message, "content") else ""
                    artifact = getattr(message, "artifact", None)

                    # 尝试解析 content 为 JSON
                    try:
                        output = json.loads(content_str) if content_str else {}
                    except json.JSONDecodeError:
                        output = {"result": content_str}

                    yield builder.tool_output_available(tool_call_id, output, artifact)
                    continue

                # 普通 AI token -> 文本流
                text_content = str(message.content) if hasattr(message, "content") else ""
                if text_content:
                    # 如果是第一个文本 token，先发送 text-start
                    if not builder.text_started:
                        yield builder.text_start()
                    yield builder.text_delta(text_content)
                continue

            # 处理 dict 格式 (updates 模式)
            if isinstance(chunk, dict) and chunk.get("mode") == "updates":
                data = chunk.get("data", {})

                for _node_name, node_data in data.items():
                    if isinstance(node_data, dict) and "messages" in node_data:
                        messages = node_data["messages"]
                        if not isinstance(messages, list):
                            messages = [messages]

                        for msg in messages:
                            serialized = _serialize_message(msg)

                            # 处理工具调用
                            if serialized.get("tool_calls"):
                                if builder.text_started:
                                    yield builder.text_end()

                                for tool_call in serialized["tool_calls"]:
                                    tool_call_id = tool_call.get("id", f"call_{uuid.uuid4().hex[:8]}")
                                    tool_name = tool_call.get("name", "unknown")
                                    tool_args = tool_call.get("args", {})

                                    yield builder.tool_input_start(tool_call_id, tool_name)
                                    yield builder.tool_input_available(tool_call_id, tool_name, tool_args)

                            # 处理工具结果
                            elif serialized.get("tool_call_id"):
                                tool_call_id = serialized["tool_call_id"]
                                content_str = serialized.get("content", "")
                                artifact = serialized.get("artifact")

                                try:
                                    output = json.loads(content_str) if content_str else {}
                                except json.JSONDecodeError:
                                    output = {"result": content_str}

                                yield builder.tool_output_available(tool_call_id, output, artifact)

        # 如果文本块未结束，结束它
        if builder.text_started:
            yield builder.text_end()

        # 发送步骤和消息结束
        yield builder.finish_step()
        yield builder.finish()

    except Exception as e:
        yield builder.error(str(e))

    finally:
        # 发送流结束标记
        yield builder.done()


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
            # Vercel AI SDK Data Stream Protocol header
            "x-vercel-ai-ui-message-stream": "v1",
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
