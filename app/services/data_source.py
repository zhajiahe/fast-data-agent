"""
数据源服务

处理数据源管理相关的业务逻辑
"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.data_source import DataSource, DataSourceRawMapping
from app.repositories.data_source import DataSourceRawMappingRepository, DataSourceRepository
from app.repositories.raw_data import RawDataRepository
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceListQuery,
    DataSourceUpdate,
    FieldMapping,
)


class DataSourceService:
    """数据源服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DataSourceRepository(db)
        self.mapping_repo = DataSourceRawMappingRepository(db)
        self.raw_data_repo = RawDataRepository(db)

    async def get_data_source(self, data_source_id: int, user_id: int) -> DataSource:
        """
        获取单个数据源

        Args:
            data_source_id: 数据源 ID
            user_id: 用户 ID

        Returns:
            数据源实例

        Raises:
            NotFoundException: 数据源不存在
        """
        data_source = await self.repo.get_by_id(data_source_id)
        if not data_source or data_source.user_id != user_id:
            raise NotFoundException(msg="数据源不存在")
        return data_source

    async def get_data_source_with_mappings(self, data_source_id: int, user_id: int) -> DataSource:
        """
        获取数据源（包含关联的 raw_mappings）

        Args:
            data_source_id: 数据源 ID
            user_id: 用户 ID

        Returns:
            数据源实例

        Raises:
            NotFoundException: 数据源不存在
        """
        data_source = await self.repo.get_with_mappings(data_source_id)
        if not data_source or data_source.user_id != user_id:
            raise NotFoundException(msg="数据源不存在")
        return data_source

    async def get_data_sources(
        self,
        user_id: int,
        query_params: DataSourceListQuery,
        page_num: int = 1,
        page_size: int = 10,
    ) -> tuple[list[DataSource], int]:
        """
        获取数据源列表

        Args:
            user_id: 用户 ID
            query_params: 查询参数
            page_num: 页码
            page_size: 每页数量

        Returns:
            (数据源列表, 总数) 元组
        """
        skip = (page_num - 1) * page_size
        return await self.repo.search(
            user_id,
            keyword=query_params.keyword,
            category=query_params.category,
            skip=skip,
            limit=page_size,
        )

    async def create_data_source(self, user_id: int, data: DataSourceCreate) -> DataSource:
        """
        创建数据源

        Args:
            user_id: 用户 ID
            data: 创建数据

        Returns:
            创建的数据源实例

        Raises:
            BadRequestException: 数据验证失败
        """
        # 检查名称是否已存在
        if await self.repo.name_exists(data.name, user_id):
            raise BadRequestException(msg="数据源名称已存在")

        # 验证所有 raw_data_ids
        if data.raw_mappings:
            raw_ids = [m.raw_data_id for m in data.raw_mappings]
            raw_data_list = await self.raw_data_repo.get_by_ids(raw_ids, user_id)
            found_ids = {rd.id for rd in raw_data_list}
            missing_ids = set(raw_ids) - found_ids
            if missing_ids:
                raise BadRequestException(msg=f"原始数据不存在: {missing_ids}")

        # 构建创建数据
        create_data: dict[str, Any] = {
            "name": data.name,
            "description": data.description,
            "category": data.category.value if data.category else None,
            "user_id": user_id,
            "target_fields": [f.model_dump() for f in data.target_fields] if data.target_fields else None,
        }

        # 创建数据源
        data_source = await self.repo.create(create_data)

        # 创建映射关系
        await self._create_mappings(data_source.id, data.raw_mappings)

        return data_source

    async def update_data_source(
        self,
        data_source_id: int,
        user_id: int,
        data: DataSourceUpdate,
    ) -> DataSource:
        """
        更新数据源

        Args:
            data_source_id: 数据源 ID
            user_id: 用户 ID
            data: 更新数据

        Returns:
            更新后的数据源实例

        Raises:
            NotFoundException: 数据源不存在
            BadRequestException: 数据验证失败
        """
        data_source = await self.get_data_source(data_source_id, user_id)

        # 检查名称是否已存在
        if data.name and await self.repo.name_exists(data.name, user_id, exclude_id=data_source_id):
            raise BadRequestException(msg="数据源名称已存在")

        # 验证所有 raw_data_ids
        if data.raw_mappings:
            raw_ids = [m.raw_data_id for m in data.raw_mappings]
            raw_data_list = await self.raw_data_repo.get_by_ids(raw_ids, user_id)
            found_ids = {rd.id for rd in raw_data_list}
            missing_ids = set(raw_ids) - found_ids
            if missing_ids:
                raise BadRequestException(msg=f"原始数据不存在: {missing_ids}")

        # 构建更新数据
        update_data: dict[str, Any] = {}

        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.category is not None:
            update_data["category"] = data.category.value
        if data.target_fields is not None:
            update_data["target_fields"] = [f.model_dump() for f in data.target_fields]

        if update_data:
            data_source = await self.repo.update(data_source, update_data)

        # 更新映射关系
        if data.raw_mappings is not None:
            # 删除旧映射
            await self.mapping_repo.delete_by_data_source(data_source_id)
            # 创建新映射
            await self._create_mappings(data_source_id, data.raw_mappings)

        return data_source

    async def _create_mappings(
        self,
        data_source_id: int,
        mappings: list[FieldMapping],
    ) -> list[DataSourceRawMapping]:
        """创建映射关系"""
        created_mappings = []
        for mapping in mappings:
            mapping_data: dict[str, Any] = {
                "data_source_id": data_source_id,
                "raw_data_id": mapping.raw_data_id,
                "field_mappings": mapping.mappings,
                "priority": mapping.priority,
                "is_enabled": mapping.is_enabled,
            }
            created = await self.mapping_repo.create(mapping_data)
            created_mappings.append(created)
        return created_mappings

    async def delete_data_source(self, data_source_id: int, user_id: int) -> None:
        """
        删除数据源

        Args:
            data_source_id: 数据源 ID
            user_id: 用户 ID

        Raises:
            NotFoundException: 数据源不存在
        """
        # 验证权限
        await self.get_data_source(data_source_id, user_id)

        # 删除映射关系
        await self.mapping_repo.delete_by_data_source(data_source_id)

        # 删除数据源
        success = await self.repo.delete(data_source_id, soft_delete=True)
        if not success:
            raise NotFoundException(msg="数据源不存在")

    async def update_schema_cache(
        self,
        data_source_id: int,
        user_id: int,
        schema_cache: dict[str, Any],
    ) -> DataSource:
        """
        更新 Schema 缓存

        Args:
            data_source_id: 数据源 ID
            user_id: 用户 ID
            schema_cache: Schema 缓存数据

        Returns:
            更新后的数据源实例
        """
        data_source = await self.get_data_source(data_source_id, user_id)

        # 添加同步时间
        schema_cache["synced_at"] = datetime.now().isoformat()

        return await self.repo.update(data_source, {"schema_cache": schema_cache})

    async def get_data_sources_by_ids(self, ids: list[int], user_id: int) -> list[DataSource]:
        """
        根据 ID 列表获取数据源

        Args:
            ids: ID 列表
            user_id: 用户 ID

        Returns:
            数据源列表
        """
        return await self.repo.get_by_ids(ids, user_id)
