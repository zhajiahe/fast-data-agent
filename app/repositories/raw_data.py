"""
数据对象 Repository

封装数据对象相关的数据库操作
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.raw_data import RawData, RawDataType
from app.repositories.base import BaseRepository


class RawDataRepository(BaseRepository[RawData]):
    """数据对象数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(RawData, db)

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RawData]:
        """获取用户的数据对象列表"""
        return await self.get_all(skip=skip, limit=limit, filters={"user_id": user_id})

    async def search(
        self,
        user_id: uuid.UUID,
        *,
        keyword: str | None = None,
        raw_type: RawDataType | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[RawData], int]:
        """
        搜索数据对象

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            raw_type: 数据对象类型
            status: 状态
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (数据对象列表, 总数) 元组
        """
        # 基础查询
        base_filter = [RawData.user_id == user_id, RawData.deleted == 0]

        # 关键词搜索
        if keyword:
            base_filter.append(
                or_(
                    RawData.name.like(f"%{keyword}%"),
                    RawData.description.like(f"%{keyword}%"),
                )
            )

        # 类型过滤
        if raw_type:
            base_filter.append(RawData.raw_type == raw_type.value)

        # 状态过滤
        if status:
            base_filter.append(RawData.status == status)

        # 获取总数
        count_query = select(func.count()).select_from(RawData).where(*base_filter)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页查询
        query = select(RawData).where(*base_filter).order_by(RawData.create_time.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_ids(self, ids: list[uuid.UUID], user_id: uuid.UUID) -> list[RawData]:
        """
        根据 ID 列表获取数据对象

        Args:
            ids: ID 列表
            user_id: 用户 ID

        Returns:
            数据对象列表
        """
        query = select(RawData).where(
            RawData.id.in_(ids),
            RawData.user_id == user_id,
            RawData.deleted == 0,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def exists_by_connection(self, connection_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """是否存在使用指定数据库连接的 RawData。"""
        query = (
            select(func.count())
            .select_from(RawData)
            .where(
                RawData.connection_id == connection_id,
                RawData.user_id == user_id,
                RawData.deleted == 0,
            )
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def get_with_relations(self, id: uuid.UUID) -> RawData | None:
        """
        获取数据对象（包含关联的 connection 和 uploaded_file）

        Args:
            id: 数据对象 ID

        Returns:
            数据对象实例或 None
        """
        query = (
            select(RawData)
            .options(
                selectinload(RawData.connection),
                selectinload(RawData.uploaded_file),
            )
            .where(RawData.id == id, RawData.deleted == 0)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def name_exists(self, name: str, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None) -> bool:
        """检查数据对象名称是否已存在"""
        query = select(RawData).where(
            RawData.name == name,
            RawData.user_id == user_id,
            RawData.deleted == 0,
        )
        if exclude_id:
            query = query.where(RawData.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def exists_by_file(self, file_id: uuid.UUID) -> bool:
        """
        检查是否有 RawData 引用指定的上传文件

        Args:
            file_id: 上传文件 ID

        Returns:
            是否存在引用
        """
        query = (
            select(func.count())
            .select_from(RawData)
            .where(
                RawData.file_id == file_id,
                RawData.deleted == 0,
            )
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def get_by_ids_with_relations(self, ids: list[uuid.UUID], user_id: uuid.UUID) -> list[RawData]:
        """
        根据 ID 列表获取数据对象（包含关联的 connection 和 uploaded_file）

        Args:
            ids: ID 列表
            user_id: 用户 ID

        Returns:
            数据对象列表
        """
        if not ids:
            return []

        query = (
            select(RawData)
            .options(
                selectinload(RawData.connection),
                selectinload(RawData.uploaded_file),
            )
            .where(
                RawData.id.in_(ids),
                RawData.user_id == user_id,
                RawData.deleted == 0,
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def has_session_references(self, raw_data_id: uuid.UUID) -> bool:
        """
        检查是否有会话引用该数据对象

        只检查未删除的会话中的引用，软删除的会话不计入。

        Args:
            raw_data_id: 数据对象 ID

        Returns:
            是否存在引用
        """
        from app.models.session import AnalysisSession, SessionRawData

        query = (
            select(func.count())
            .select_from(SessionRawData)
            .join(AnalysisSession, SessionRawData.session_id == AnalysisSession.id)
            .where(
                SessionRawData.raw_data_id == raw_data_id,
                SessionRawData.deleted == 0,
                AnalysisSession.deleted == 0,  # 排除软删除的会话
            )
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0
