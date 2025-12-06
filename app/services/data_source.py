"""
数据源服务

处理数据源管理相关的业务逻辑
"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.data_source import DataSource, DataSourceType
from app.repositories.data_source import DataSourceRepository
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceListQuery,
    DataSourceUpdate,
)


class DataSourceService:
    """数据源服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DataSourceRepository(db)

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
            source_type=query_params.source_type,
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

        # 验证数据
        if data.source_type == DataSourceType.DATABASE:
            if not data.db_config:
                raise BadRequestException(msg="数据库类型数据源必须提供连接配置")
        elif data.source_type == DataSourceType.FILE:
            if not data.file_id:
                raise BadRequestException(msg="文件类型数据源必须关联文件")

        # 构建创建数据
        create_data: dict[str, Any] = {
            "name": data.name,
            "description": data.description,
            "source_type": data.source_type.value,
            "user_id": user_id,
            "group_name": data.group_name,
        }

        # 数据库连接配置
        if data.db_config:
            create_data.update(
                {
                    "db_type": data.db_config.db_type.value,
                    "host": data.db_config.host,
                    "port": data.db_config.port,
                    "database": data.db_config.database,
                    "username": data.db_config.username,
                    "password": data.db_config.password,  # TODO: 加密存储
                    "extra_params": data.db_config.extra_params,
                }
            )

        # 文件关联
        if data.file_id:
            create_data["file_id"] = data.file_id

        return await self.repo.create(create_data)

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

        # 构建更新数据
        update_data: dict[str, Any] = {}

        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.group_name is not None:
            update_data["group_name"] = data.group_name

        # 数据库连接配置更新
        if data.db_config:
            update_data.update(
                {
                    "db_type": data.db_config.db_type.value,
                    "host": data.db_config.host,
                    "port": data.db_config.port,
                    "database": data.db_config.database,
                    "username": data.db_config.username,
                    "password": data.db_config.password,
                    "extra_params": data.db_config.extra_params,
                }
            )

        if update_data:
            data_source = await self.repo.update(data_source, update_data)

        return data_source

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

    async def get_data_source_with_file(self, data_source_id: int, user_id: int) -> DataSource:
        """
        获取数据源（包含关联文件）

        Args:
            data_source_id: 数据源 ID
            user_id: 用户 ID

        Returns:
            数据源实例

        Raises:
            NotFoundException: 数据源不存在
        """
        data_source = await self.repo.get_with_file(data_source_id)
        if not data_source or data_source.user_id != user_id:
            raise NotFoundException(msg="数据源不存在")
        return data_source


