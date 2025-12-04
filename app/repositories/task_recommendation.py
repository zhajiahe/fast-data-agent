"""
任务推荐 Repository

封装 TaskRecommendation 相关的数据库操作
"""

from typing import Any, cast

from sqlalchemy import CursorResult, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_recommendation import (
    RecommendationSourceType,
    RecommendationStatus,
    TaskRecommendation,
)
from app.repositories.base import BaseRepository


class TaskRecommendationRepository(BaseRepository[TaskRecommendation]):
    """任务推荐数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(TaskRecommendation, db)

    async def get_by_session(
        self,
        session_id: int,
        *,
        status: str | None = None,
        source_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TaskRecommendation]:
        """
        获取会话的推荐列表

        Args:
            session_id: 会话 ID
            status: 过滤状态
            source_type: 过滤来源类型
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            推荐列表（按优先级升序）
        """
        query = select(TaskRecommendation).where(
            TaskRecommendation.session_id == session_id,
            TaskRecommendation.deleted == 0,
        )

        if status:
            query = query.where(TaskRecommendation.status == status)
        if source_type:
            query = query.where(TaskRecommendation.source_type == source_type)

        query = query.order_by(TaskRecommendation.priority.asc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_session(
        self,
        session_id: int,
        *,
        status: str | None = None,
        source_type: str | None = None,
    ) -> int:
        """获取会话推荐总数"""
        from sqlalchemy import func

        query = select(func.count()).where(
            TaskRecommendation.session_id == session_id,
            TaskRecommendation.deleted == 0,
        )

        if status:
            query = query.where(TaskRecommendation.status == status)
        if source_type:
            query = query.where(TaskRecommendation.source_type == source_type)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_pending_by_session(self, session_id: int) -> list[TaskRecommendation]:
        """获取会话中待选择的推荐"""
        return await self.get_by_session(
            session_id,
            status=RecommendationStatus.PENDING.value,
        )

    async def update_status(
        self,
        recommendation_id: int,
        status: RecommendationStatus,
    ) -> TaskRecommendation | None:
        """
        更新推荐状态

        Args:
            recommendation_id: 推荐 ID
            status: 新状态

        Returns:
            更新后的推荐对象，或 None
        """
        recommendation = await self.get_by_id(recommendation_id)
        if recommendation:
            return await self.update(recommendation, {"status": status.value})
        return None

    async def dismiss_by_session(
        self,
        session_id: int,
        source_type: str | None = None,
    ) -> int:
        """
        批量忽略会话中的推荐

        Args:
            session_id: 会话 ID
            source_type: 可选过滤来源类型

        Returns:
            更新的记录数
        """
        from sqlalchemy import update

        query = (
            update(TaskRecommendation)
            .where(
                TaskRecommendation.session_id == session_id,
                TaskRecommendation.status == RecommendationStatus.PENDING.value,
                TaskRecommendation.deleted == 0,
            )
            .values(status=RecommendationStatus.DISMISSED.value)
        )

        if source_type:
            query = query.where(TaskRecommendation.source_type == source_type)

        result = await self.db.execute(query)
        await self.db.commit()
        cursor = cast(CursorResult[Any], result)
        return cursor.rowcount if cursor.rowcount else 0

    async def delete_by_session(
        self,
        session_id: int,
        source_type: str | None = None,
    ) -> int:
        """
        软删除会话中的推荐（用于重新生成前清理）

        Args:
            session_id: 会话 ID
            source_type: 可选过滤来源类型

        Returns:
            删除的记录数
        """
        from sqlalchemy import update

        query = (
            update(TaskRecommendation)
            .where(
                TaskRecommendation.session_id == session_id,
                TaskRecommendation.deleted == 0,
            )
            .values(deleted=1)
        )

        if source_type:
            query = query.where(TaskRecommendation.source_type == source_type)

        result = await self.db.execute(query)
        await self.db.commit()
        cursor = cast(CursorResult[Any], result)
        return cursor.rowcount if cursor.rowcount else 0

    async def create_from_items(
        self,
        session_id: int,
        items: list[dict],
        user_id: int,
        trigger_message_id: int | None = None,
    ) -> list[TaskRecommendation]:
        """
        从推荐项列表批量创建推荐

        Args:
            session_id: 会话 ID
            items: 推荐项列表（包含 title, description, category, priority, source_type）
            user_id: 用户 ID
            trigger_message_id: 触发消息 ID（追问推荐时）

        Returns:
            创建的推荐列表
        """
        created = []
        for item in items:
            data = {
                "session_id": session_id,
                "title": item.get("title", ""),
                "description": item.get("description"),
                "category": item.get("category", "other"),
                "source_type": item.get("source_type", RecommendationSourceType.INITIAL.value),
                "priority": item.get("priority", 0),
                "status": RecommendationStatus.PENDING.value,
                "trigger_message_id": trigger_message_id,
                "create_by": user_id,
                "update_by": user_id,
            }
            recommendation = await self.create(data)
            created.append(recommendation)
        return created

