"""
聊天消息 Repository

封装 ChatMessage 相关的数据库操作
"""

import uuid

from langchain_core.messages import BaseMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import ChatMessage
from app.repositories.base import BaseRepository
from app.utils.message_converter import MessageConverter


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """聊天消息数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(ChatMessage, db)

    async def get_by_session(
        self,
        session_id: uuid.UUID,
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
            消息列表（按序号升序，确保消息顺序正确）
        """
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.deleted == 0)
            .order_by(ChatMessage.seq.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_session(self, session_id: uuid.UUID) -> int:
        """获取会话消息总数"""
        from sqlalchemy import func

        query = select(func.count()).where(
            ChatMessage.session_id == session_id,
            ChatMessage.deleted == 0,
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def clear_by_session(self, session_id: uuid.UUID) -> int:
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
        return getattr(result, "rowcount", 0) or 0

    async def get_next_seq(self, session_id: uuid.UUID) -> int:
        """
        获取会话的下一个消息序号

        Args:
            session_id: 会话 ID

        Returns:
            下一个序号值（当前最大 seq + 1）
        """
        from sqlalchemy import func

        query = select(func.coalesce(func.max(ChatMessage.seq), 0)).where(ChatMessage.session_id == session_id)
        result = await self.db.execute(query)
        max_seq = result.scalar() or 0
        return max_seq + 1

    async def save_langchain_message(
        self,
        session_id: uuid.UUID,
        message: BaseMessage,
        user_id: uuid.UUID,
        *,
        seq: int | None = None,
    ) -> ChatMessage:
        """
        保存 LangChain 消息到数据库

        Args:
            session_id: 会话 ID
            message: LangChain 消息对象
            user_id: 用户 ID（用于 create_by）
            seq: 消息序号（可选，不提供则自动获取下一个）

        Returns:
            保存的 ChatMessage 对象
        """
        # 获取序号（如果未提供）
        if seq is None:
            seq = await self.get_next_seq(session_id)

        # 使用转换器构建数据
        data = MessageConverter.from_langchain_message(message, session_id, user_id, seq)

        return await self.create(data)

    async def save_langchain_messages(
        self,
        session_id: uuid.UUID,
        messages: list[BaseMessage],
        user_id: uuid.UUID,
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
        if not messages:
            return []

        # 先获取下一个 seq，然后为每条消息分配递增的序号
        next_seq = await self.get_next_seq(session_id)

        saved = []
        for i, message in enumerate(messages):
            chat_message = await self.save_langchain_message(session_id, message, user_id, seq=next_seq + i)
            saved.append(chat_message)
        return saved

    def to_langchain_message(self, chat_message: ChatMessage) -> BaseMessage:
        """
        将 ChatMessage 转换为 LangChain 消息

        注：此方法委托给 MessageConverter，保留是为了向后兼容。
        新代码应直接使用 MessageConverter.to_langchain_message()。
        """
        return MessageConverter.to_langchain_message(chat_message)

    def to_langchain_messages(self, chat_messages: list[ChatMessage]) -> list[BaseMessage]:
        """
        批量转换为 LangChain 消息

        注：此方法委托给 MessageConverter，保留是为了向后兼容。
        新代码应直接使用 MessageConverter.to_langchain_messages()。
        """
        return MessageConverter.to_langchain_messages(chat_messages)

    async def get_by_sessions_batch(
        self,
        session_ids: list[uuid.UUID],
        *,
        limit_per_session: int = 100,
    ) -> dict[uuid.UUID, list[ChatMessage]]:
        """
        批量获取多个会话的消息

        Args:
            session_ids: 会话 ID 列表
            limit_per_session: 每个会话的消息数量上限

        Returns:
            会话ID -> 消息列表 的字典
        """

        if not session_ids:
            return {}

        # 使用窗口函数获取每个会话的前 N 条消息
        # 这比多次查询效率更高

        # 简化实现：批量查询，然后在内存中分组
        query = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id.in_(session_ids),
                ChatMessage.deleted == 0,
            )
            .order_by(ChatMessage.session_id, ChatMessage.seq.asc())
        )
        result = await self.db.execute(query)
        all_messages = list(result.scalars().all())

        # 按会话分组并限制数量
        grouped: dict[uuid.UUID, list[ChatMessage]] = {sid: [] for sid in session_ids}
        for msg in all_messages:
            if msg.session_id in grouped and len(grouped[msg.session_id]) < limit_per_session:
                grouped[msg.session_id].append(msg)

        return grouped

    async def count_by_sessions_batch(
        self,
        session_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, int]:
        """
        批量获取多个会话的消息总数

        Args:
            session_ids: 会话 ID 列表

        Returns:
            会话ID -> 消息数量 的字典
        """
        from sqlalchemy import func

        if not session_ids:
            return {}

        query = (
            select(ChatMessage.session_id, func.count(ChatMessage.id).label("count"))
            .where(
                ChatMessage.session_id.in_(session_ids),
                ChatMessage.deleted == 0,
            )
            .group_by(ChatMessage.session_id)
        )
        result = await self.db.execute(query)
        rows = result.all()

        # 构建结果字典，未找到的会话返回 0
        counts: dict[uuid.UUID, int] = dict.fromkeys(session_ids, 0)
        for row in rows:
            counts[row.session_id] = row.count  # type: ignore[assignment]

        return counts
