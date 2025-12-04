"""
分析会话 Repository

封装分析会话相关的数据库操作
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import AnalysisSession
from app.repositories.base import BaseRepository


class AnalysisSessionRepository(BaseRepository[AnalysisSession]):
    """分析会话数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(AnalysisSession, db)

    async def search(
        self,
        user_id: int,
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

    async def increment_message_count(self, session_id: int) -> None:
        """增加消息计数"""
        session = await self.get_by_id(session_id)
        if session:
            session.message_count += 1
            await self.db.flush()
