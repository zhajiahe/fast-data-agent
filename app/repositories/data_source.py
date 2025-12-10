"""
数据源 Repository

封装数据源相关的数据库操作
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.data_source import DataSource, DataSourceCategory, DataSourceRawMapping
from app.models.raw_data import RawData
from app.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    """数据源数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(DataSource, db)

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DataSource]:
        """获取用户的数据源列表"""
        return await self.get_all(skip=skip, limit=limit, filters={"user_id": user_id})

    async def search(
        self,
        user_id: uuid.UUID,
        *,
        keyword: str | None = None,
        category: DataSourceCategory | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[DataSource], int]:
        """
        搜索数据源

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            category: 数据源分类
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (数据源列表, 总数) 元组
        """
        # 基础查询
        base_filter = [DataSource.user_id == user_id, DataSource.deleted == 0]

        # 关键词搜索
        if keyword:
            base_filter.append(
                or_(
                    DataSource.name.like(f"%{keyword}%"),
                    DataSource.description.like(f"%{keyword}%"),
                )
            )

        # 分类过滤
        if category:
            base_filter.append(DataSource.category == category.value)

        # 获取总数
        count_query = select(func.count()).select_from(DataSource).where(*base_filter)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页查询
        query = select(DataSource).where(*base_filter).order_by(DataSource.create_time.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_ids(self, ids: list[uuid.UUID], user_id: uuid.UUID) -> list[DataSource]:
        """
        根据 ID 列表获取数据源（包含关联的 raw_mappings、raw_data 及其依赖）

        Args:
            ids: ID 列表
            user_id: 用户 ID

        Returns:
            数据源列表
        """
        # 预加载完整的关系链：
        # DataSource -> raw_mappings -> raw_data -> (uploaded_file, connection)
        raw_data_loader = selectinload(DataSourceRawMapping.raw_data).options(
            selectinload(RawData.uploaded_file),
            selectinload(RawData.connection),
        )
        query = (
            select(DataSource)
            .options(selectinload(DataSource.raw_mappings).options(raw_data_loader))
            .where(
                DataSource.id.in_(ids),
                DataSource.user_id == user_id,
                DataSource.deleted == 0,
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_mappings(self, id: uuid.UUID) -> DataSource | None:
        """
        获取数据源（包含关联的 raw_mappings、raw_data 及其依赖）

        Args:
            id: 数据源 ID

        Returns:
            数据源实例或 None
        """
        # 预加载完整的关系链：
        # DataSource -> raw_mappings -> raw_data -> (uploaded_file, connection)
        raw_data_loader = selectinload(DataSourceRawMapping.raw_data).options(
            selectinload(RawData.uploaded_file),
            selectinload(RawData.connection),
        )
        query = (
            select(DataSource)
            .options(selectinload(DataSource.raw_mappings).options(raw_data_loader))
            .where(DataSource.id == id, DataSource.deleted == 0)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def name_exists(self, name: str, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None) -> bool:
        """检查数据源名称是否已存在"""
        query = select(DataSource).where(
            DataSource.name == name,
            DataSource.user_id == user_id,
            DataSource.deleted == 0,
        )
        if exclude_id:
            query = query.where(DataSource.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None


class DataSourceRawMappingRepository(BaseRepository[DataSourceRawMapping]):
    """数据源-原始数据映射数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(DataSourceRawMapping, db)

    async def get_by_data_source(self, data_source_id: uuid.UUID) -> list[DataSourceRawMapping]:
        """获取数据源的所有映射"""
        query = (
            select(DataSourceRawMapping)
            .options(selectinload(DataSourceRawMapping.raw_data))
            .where(
                DataSourceRawMapping.data_source_id == data_source_id,
                DataSourceRawMapping.deleted == 0,
            )
            .order_by(DataSourceRawMapping.priority.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_by_data_source(self, data_source_id: uuid.UUID) -> int:
        """删除数据源的所有映射（软删除）"""
        query = select(DataSourceRawMapping).where(
            DataSourceRawMapping.data_source_id == data_source_id,
            DataSourceRawMapping.deleted == 0,
        )
        result = await self.db.execute(query)
        mappings = result.scalars().all()

        count = 0
        for mapping in mappings:
            mapping.deleted = 1
            count += 1

        await self.db.flush()
        return count

    async def exists_by_raw_data(self, raw_data_id: uuid.UUID) -> bool:
        """是否存在引用指定 RawData 的映射。"""
        query = (
            select(func.count())
            .select_from(DataSourceRawMapping)
            .where(
                DataSourceRawMapping.raw_data_id == raw_data_id,
                DataSourceRawMapping.deleted == 0,
            )
        )
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0
