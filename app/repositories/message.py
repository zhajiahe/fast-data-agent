"""
聊天消息 Repository

封装 ChatMessage 相关的数据库操作
"""

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import ChatMessage, MessageType
from app.repositories.base import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """聊天消息数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(ChatMessage, db)

    async def get_by_session(
        self,
        session_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ChatMessage]:
        """
        获取会话的消息列表

        Args:
            session_id: 会话 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            消息列表（按创建时间升序）
        """
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.deleted == 0)
            .order_by(ChatMessage.create_time.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_session(self, session_id: int) -> int:
        """获取会话消息总数"""
        from sqlalchemy import func

        query = select(func.count()).where(
            ChatMessage.session_id == session_id,
            ChatMessage.deleted == 0,
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def clear_by_session(self, session_id: int) -> int:
        """
        清空会话的所有消息（硬删除）

        Args:
            session_id: 会话 ID

        Returns:
            删除的消息数量
        """
        from sqlalchemy import delete

        query = delete(ChatMessage).where(ChatMessage.session_id == session_id)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount or 0

    async def save_langchain_message(
        self,
        session_id: int,
        message: BaseMessage,
        user_id: int,
    ) -> ChatMessage:
        """
        保存 LangChain 消息到数据库

        Args:
            session_id: 会话 ID
            message: LangChain 消息对象
            user_id: 用户 ID（用于 create_by）

        Returns:
            保存的 ChatMessage 对象
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

        return await self.create(data)

    async def save_langchain_messages(
        self,
        session_id: int,
        messages: list[BaseMessage],
        user_id: int,
    ) -> list[ChatMessage]:
        """
        批量保存 LangChain 消息

        Args:
            session_id: 会话 ID
            messages: LangChain 消息列表
            user_id: 用户 ID

        Returns:
            保存的 ChatMessage 列表
        """
        saved = []
        for message in messages:
            chat_message = await self.save_langchain_message(session_id, message, user_id)
            saved.append(chat_message)
        return saved

    def to_langchain_message(self, chat_message: ChatMessage) -> BaseMessage:
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

    def to_langchain_messages(self, chat_messages: list[ChatMessage]) -> list[BaseMessage]:
        """
        批量转换为 LangChain 消息

        Args:
            chat_messages: 数据库消息列表

        Returns:
            LangChain 消息列表
        """
        return [self.to_langchain_message(m) for m in chat_messages]
