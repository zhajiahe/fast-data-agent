"""
分析会话 Repository

封装分析会话相关的数据库操作
"""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import AnalysisSession
from app.repositories.base import BaseRepository


class AnalysisSessionRepository(BaseRepository[AnalysisSession]):
    """分析会话数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(AnalysisSession, db)

    async def get_with_raw_data_links(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AnalysisSession | None:
        """
        获取会话及其关联的 SessionRawData（Eager load）

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            会话实例或 None
        """
        query = (
            select(AnalysisSession)
            .options(selectinload(AnalysisSession.raw_data_links))
            .where(
                AnalysisSession.id == session_id,
                AnalysisSession.user_id == user_id,
                AnalysisSession.deleted == 0,
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search(
        self,
        user_id: uuid.UUID,
        *,
        keyword: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AnalysisSession], int]:
        """
        搜索分析会话

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            status: 会话状态
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (会话列表, 总数) 元组
        """
        from sqlalchemy import func

        # 基础查询
        query = select(AnalysisSession).where(AnalysisSession.user_id == user_id, AnalysisSession.deleted == 0)
        count_query = select(AnalysisSession).where(AnalysisSession.user_id == user_id, AnalysisSession.deleted == 0)

        # 关键词搜索
        if keyword:
            keyword_filter = or_(
                AnalysisSession.name.like(f"%{keyword}%"),
                AnalysisSession.description.like(f"%{keyword}%"),
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)

        # 状态过滤
        if status:
            query = query.where(AnalysisSession.status == status)
            count_query = count_query.where(AnalysisSession.status == status)

        # 获取总数
        count_result = await self.db.execute(select(func.count()).select_from(count_query.subquery()))
        total = count_result.scalar() or 0

        # 分页查询
        query = query.order_by(AnalysisSession.update_time.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def increment_message_count(self, session_id: uuid.UUID) -> None:
        """增加消息计数"""
        session = await self.get_by_id(session_id)
        if session:
            session.message_count += 1
            await self.db.flush()

    async def get_by_ids_and_user(
        self,
        session_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> list[AnalysisSession]:
        """
        根据 ID 列表和用户 ID 获取会话

        只返回属于指定用户的会话，用于批量操作时的权限验证。

        Args:
            session_ids: 会话 ID 列表
            user_id: 用户 ID

        Returns:
            属于该用户的会话列表
        """
        if not session_ids:
            return []

        query = select(AnalysisSession).where(
            AnalysisSession.id.in_(session_ids),
            AnalysisSession.user_id == user_id,
            AnalysisSession.deleted == 0,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
