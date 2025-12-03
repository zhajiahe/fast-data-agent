"""
数据源 Repository

封装数据源相关的数据库操作
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import DataSource, DataSourceType
from app.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    """数据源数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(DataSource, db)

    async def get_by_user(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DataSource]:
        """
        获取用户的数据源列表

        Args:
            user_id: 用户 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            数据源列表
        """
        return await self.get_all(skip=skip, limit=limit, filters={"user_id": user_id})

    async def search(
        self,
        user_id: int,
        *,
        keyword: str | None = None,
        source_type: DataSourceType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[DataSource], int]:
        """
        搜索数据源

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            source_type: 数据源类型
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (数据源列表, 总数) 元组
        """
        from sqlalchemy import func

        # 基础查询
        query = select(DataSource).where(DataSource.user_id == user_id, DataSource.deleted == 0)
        count_query = select(DataSource).where(DataSource.user_id == user_id, DataSource.deleted == 0)

        # 关键词搜索
        if keyword:
            keyword_filter = or_(
                DataSource.name.like(f"%{keyword}%"),
                DataSource.description.like(f"%{keyword}%"),
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)

        # 类型过滤
        if source_type:
            query = query.where(DataSource.source_type == source_type.value)
            count_query = count_query.where(DataSource.source_type == source_type.value)

        # 获取总数
        count_result = await self.db.execute(select(func.count()).select_from(count_query.subquery()))
        total = count_result.scalar() or 0

        # 分页查询
        query = query.order_by(DataSource.create_time.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_ids(self, ids: list[int], user_id: int) -> list[DataSource]:
        """
        根据 ID 列表获取数据源

        Args:
            ids: ID 列表
            user_id: 用户 ID（确保只能获取自己的数据源）

        Returns:
            数据源列表
        """
        query = select(DataSource).where(
            DataSource.id.in_(ids),
            DataSource.user_id == user_id,
            DataSource.deleted == 0,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def name_exists(self, name: str, user_id: int, exclude_id: int | None = None) -> bool:
        """
        检查数据源名称是否已存在

        Args:
            name: 数据源名称
            user_id: 用户 ID
            exclude_id: 排除的 ID

        Returns:
            是否存在
        """
        query = select(DataSource).where(
            DataSource.name == name,
            DataSource.user_id == user_id,
            DataSource.deleted == 0,
        )
        if exclude_id:
            query = query.where(DataSource.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
