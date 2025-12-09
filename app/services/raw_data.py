"""
原始数据服务

处理原始数据管理相关的业务逻辑
"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.raw_data import RawData, RawDataType
from app.repositories.database_connection import DatabaseConnectionRepository
from app.repositories.raw_data import RawDataRepository
from app.repositories.uploaded_file import UploadedFileRepository
from app.schemas.raw_data import (
    RawDataColumnUpdate,
    RawDataCreate,
    RawDataListQuery,
    RawDataUpdate,
)


class RawDataService:
    """原始数据服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RawDataRepository(db)
        self.connection_repo = DatabaseConnectionRepository(db)
        self.file_repo = UploadedFileRepository(db)

    async def get_raw_data(self, raw_data_id: int, user_id: int) -> RawData:
        """
        获取单个原始数据

        Args:
            raw_data_id: 原始数据 ID
            user_id: 用户 ID

        Returns:
            原始数据实例

        Raises:
            NotFoundException: 原始数据不存在
        """
        raw_data = await self.repo.get_by_id(raw_data_id)
        if not raw_data or raw_data.user_id != user_id:
            raise NotFoundException(msg="原始数据不存在")
        return raw_data

    async def get_raw_data_with_relations(self, raw_data_id: int, user_id: int) -> RawData:
        """
        获取原始数据（包含关联的 connection 和 uploaded_file）

        Args:
            raw_data_id: 原始数据 ID
            user_id: 用户 ID

        Returns:
            原始数据实例

        Raises:
            NotFoundException: 原始数据不存在
        """
        raw_data = await self.repo.get_with_relations(raw_data_id)
        if not raw_data or raw_data.user_id != user_id:
            raise NotFoundException(msg="原始数据不存在")
        return raw_data

    async def get_raw_data_list(
        self,
        user_id: int,
        query_params: RawDataListQuery,
        page_num: int = 1,
        page_size: int = 10,
    ) -> tuple[list[RawData], int]:
        """
        获取原始数据列表

        Args:
            user_id: 用户 ID
            query_params: 查询参数
            page_num: 页码
            page_size: 每页数量

        Returns:
            (原始数据列表, 总数) 元组
        """
        skip = (page_num - 1) * page_size
        return await self.repo.search(
            user_id,
            keyword=query_params.keyword,
            raw_type=query_params.raw_type,
            status=query_params.status,
            skip=skip,
            limit=page_size,
        )

    async def create_raw_data(self, user_id: int, data: RawDataCreate) -> RawData:
        """
        创建原始数据

        Args:
            user_id: 用户 ID
            data: 创建数据

        Returns:
            创建的原始数据实例

        Raises:
            BadRequestException: 数据验证失败
        """
        # 检查名称是否已存在
        if await self.repo.name_exists(data.name, user_id):
            raise BadRequestException(msg="原始数据名称已存在")

        # 构建创建数据
        create_data: dict[str, Any] = {
            "name": data.name,
            "description": data.description,
            "raw_type": data.raw_type.value,
            "user_id": user_id,
            "status": "pending",
        }

        # 数据库表类型
        if data.raw_type == RawDataType.DATABASE_TABLE:
            config = data.database_table_config
            if not config:
                raise BadRequestException(msg="数据库表类型必须提供配置")

            # 验证连接是否存在
            connection = await self.connection_repo.get_by_id(config.connection_id)
            if not connection or connection.user_id != user_id:
                raise BadRequestException(msg="数据库连接不存在")

            create_data.update(
                {
                    "connection_id": config.connection_id,
                    "schema_name": config.schema_name,
                    "table_name": config.table_name,
                    "custom_sql": config.custom_sql,
                }
            )

        # 文件类型
        elif data.raw_type == RawDataType.FILE:
            file_config = data.file_config
            if not file_config:
                raise BadRequestException(msg="文件类型必须提供配置")

            # 验证文件是否存在
            file = await self.file_repo.get_by_id(file_config.file_id)
            if not file or file.user_id != user_id:
                raise BadRequestException(msg="上传文件不存在")

            create_data["file_id"] = file_config.file_id

        return await self.repo.create(create_data)

    async def update_raw_data(
        self,
        raw_data_id: int,
        user_id: int,
        data: RawDataUpdate,
    ) -> RawData:
        """
        更新原始数据

        Args:
            raw_data_id: 原始数据 ID
            user_id: 用户 ID
            data: 更新数据

        Returns:
            更新后的原始数据实例

        Raises:
            NotFoundException: 原始数据不存在
            BadRequestException: 数据验证失败
        """
        raw_data = await self.get_raw_data(raw_data_id, user_id)

        # 检查名称是否已存在
        if data.name and await self.repo.name_exists(data.name, user_id, exclude_id=raw_data_id):
            raise BadRequestException(msg="原始数据名称已存在")

        # 构建更新数据
        update_data: dict[str, Any] = {}

        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description

        # 数据库表配置更新
        if data.database_table_config:
            config = data.database_table_config
            # 验证连接是否存在
            connection = await self.connection_repo.get_by_id(config.connection_id)
            if not connection or connection.user_id != user_id:
                raise BadRequestException(msg="数据库连接不存在")

            update_data.update(
                {
                    "connection_id": config.connection_id,
                    "schema_name": config.schema_name,
                    "table_name": config.table_name,
                    "custom_sql": config.custom_sql,
                }
            )

        # 文件配置更新
        if data.file_config:
            file_config = data.file_config
            # 验证文件是否存在
            file = await self.file_repo.get_by_id(file_config.file_id)
            if not file or file.user_id != user_id:
                raise BadRequestException(msg="上传文件不存在")

            update_data["file_id"] = file_config.file_id

        if update_data:
            raw_data = await self.repo.update(raw_data, update_data)

        return raw_data

    async def update_columns_schema(
        self,
        raw_data_id: int,
        user_id: int,
        data: RawDataColumnUpdate,
    ) -> RawData:
        """
        更新列结构（用户修正类型）

        Args:
            raw_data_id: 原始数据 ID
            user_id: 用户 ID
            data: 列结构数据

        Returns:
            更新后的原始数据实例
        """
        raw_data = await self.get_raw_data(raw_data_id, user_id)

        columns_schema = [col.model_dump() for col in data.columns]

        return await self.repo.update(raw_data, {"columns_schema": columns_schema})

    async def update_sync_status(
        self,
        raw_data_id: int,
        user_id: int,
        *,
        status: str,
        columns_schema: list[dict[str, Any]] | None = None,
        sample_data: dict[str, Any] | None = None,
        row_count_estimate: int | None = None,
        error_message: str | None = None,
    ) -> RawData:
        """
        更新同步状态

        Args:
            raw_data_id: 原始数据 ID
            user_id: 用户 ID
            status: 状态
            columns_schema: 列结构
            sample_data: 抽样数据
            row_count_estimate: 估算行数
            error_message: 错误信息

        Returns:
            更新后的原始数据实例
        """
        raw_data = await self.get_raw_data(raw_data_id, user_id)

        update_data: dict[str, Any] = {
            "status": status,
            "synced_at": datetime.now().isoformat(),
        }

        if columns_schema is not None:
            update_data["columns_schema"] = columns_schema
        if sample_data is not None:
            update_data["sample_data"] = sample_data
        if row_count_estimate is not None:
            update_data["row_count_estimate"] = row_count_estimate
        if error_message is not None:
            update_data["error_message"] = error_message

        return await self.repo.update(raw_data, update_data)

    async def delete_raw_data(self, raw_data_id: int, user_id: int) -> None:
        """
        删除原始数据

        Args:
            raw_data_id: 原始数据 ID
            user_id: 用户 ID

        Raises:
            NotFoundException: 原始数据不存在
        """
        # 验证权限
        await self.get_raw_data(raw_data_id, user_id)

        # TODO: 检查是否有 DataSource 引用此 RawData

        success = await self.repo.delete(raw_data_id, soft_delete=True)
        if not success:
            raise NotFoundException(msg="原始数据不存在")

    async def get_raw_data_by_ids(self, ids: list[int], user_id: int) -> list[RawData]:
        """
        根据 ID 列表获取原始数据

        Args:
            ids: ID 列表
            user_id: 用户 ID

        Returns:
            原始数据列表
        """
        return await self.repo.get_by_ids(ids, user_id)
