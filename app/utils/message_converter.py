"""
消息转换器

提供 ChatMessage (数据库模型) 与 LangChain BaseMessage 之间的转换功能。
这是一个工具模块，不依赖于任何 Repository 或 Service。
"""

import uuid
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.models.message import ChatMessage, MessageType


class MessageConverter:
    """消息转换器 - 负责 ChatMessage 与 LangChain 消息的双向转换"""

    @staticmethod
    def to_langchain_message(chat_message: ChatMessage) -> BaseMessage:
        """
        将 ChatMessage 转换为 LangChain 消息

        Args:
            chat_message: 数据库消息对象

        Returns:
            LangChain 消息对象
        """
        if chat_message.message_type == MessageType.HUMAN.value:
            return HumanMessage(
                content=chat_message.content,
                id=chat_message.message_id,
                name=chat_message.name,
            )

        elif chat_message.message_type == MessageType.AI.value:
            return AIMessage(
                content=chat_message.content,
                id=chat_message.message_id,
                name=chat_message.name,
                tool_calls=chat_message.tool_calls or [],
                invalid_tool_calls=chat_message.invalid_tool_calls or [],
            )

        elif chat_message.message_type == MessageType.SYSTEM.value:
            return SystemMessage(
                content=chat_message.content,
                id=chat_message.message_id,
                name=chat_message.name,
            )

        elif chat_message.message_type == MessageType.TOOL.value:
            return ToolMessage(
                content=chat_message.content,
                tool_call_id=chat_message.tool_call_id or "",
                name=chat_message.name,
                id=chat_message.message_id,
                artifact=chat_message.artifact,
                status=chat_message.status or "success",
            )

        else:
            # 默认作为 HumanMessage
            return HumanMessage(
                content=chat_message.content,
                id=chat_message.message_id,
                name=chat_message.name,
            )

    @staticmethod
    def to_langchain_messages(chat_messages: list[ChatMessage]) -> list[BaseMessage]:
        """
        批量转换为 LangChain 消息

        Args:
            chat_messages: 数据库消息列表

        Returns:
            LangChain 消息列表
        """
        return [MessageConverter.to_langchain_message(m) for m in chat_messages]

    @staticmethod
    def from_langchain_message(
        message: BaseMessage,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        seq: int,
    ) -> dict[str, Any]:
        """
        从 LangChain 消息构建 ChatMessage 创建数据

        Args:
            message: LangChain 消息对象
            session_id: 会话 ID
            user_id: 用户 ID
            seq: 消息序号

        Returns:
            用于创建 ChatMessage 的字典数据
        """
        # 确定消息类型
        if isinstance(message, HumanMessage):
            message_type = MessageType.HUMAN.value
        elif isinstance(message, AIMessage):
            message_type = MessageType.AI.value
        elif isinstance(message, SystemMessage):
            message_type = MessageType.SYSTEM.value
        elif isinstance(message, ToolMessage):
            message_type = MessageType.TOOL.value
        else:
            message_type = MessageType.AI.value  # 默认

        # 构建基础数据
        content = message.content if isinstance(message.content, str) else str(message.content)
        data: dict[str, Any] = {
            "session_id": session_id,
            "seq": seq,
            "message_type": message_type,
            "content": content,
            "message_id": getattr(message, "id", None),
            "name": getattr(message, "name", None),
            "additional_kwargs": getattr(message, "additional_kwargs", None) or None,
            "response_metadata": getattr(message, "response_metadata", None) or None,
            "create_by": str(user_id),
            "update_by": str(user_id),
        }

        # AIMessage 特有字段
        if isinstance(message, AIMessage):
            data["tool_calls"] = message.tool_calls if message.tool_calls else None
            data["invalid_tool_calls"] = message.invalid_tool_calls if message.invalid_tool_calls else None
            usage = getattr(message, "usage_metadata", None)
            data["usage_metadata"] = dict(usage) if usage else None

        # ToolMessage 特有字段
        if isinstance(message, ToolMessage):
            data["tool_call_id"] = message.tool_call_id
            data["artifact"] = getattr(message, "artifact", None)
            data["status"] = getattr(message, "status", None)

        return data

