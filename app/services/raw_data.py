"""
数据对象服务

处理数据对象管理相关的业务逻辑
"""

from datetime import datetime
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.raw_data import RawData, RawDataType
from app.repositories.data_source import DataSourceRawMappingRepository
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
    """数据对象服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RawDataRepository(db)
        self.connection_repo = DatabaseConnectionRepository(db)
        self.file_repo = UploadedFileRepository(db)
        self.mapping_repo = DataSourceRawMappingRepository(db)

    async def get_raw_data(self, raw_data_id: uuid.UUID, user_id: uuid.UUID) -> RawData:
        """
        获取单个数据对象

        Args:
            raw_data_id: 数据对象 ID
            user_id: 用户 ID

        Returns:
            数据对象实例

        Raises:
            NotFoundException: 数据对象不存在
        """
        raw_data = await self.repo.get_by_id(raw_data_id)
        if not raw_data or raw_data.user_id != user_id:
            raise NotFoundException(msg="数据对象不存在")
        return raw_data

    async def get_raw_data_with_relations(self, raw_data_id: uuid.UUID, user_id: uuid.UUID) -> RawData:
        """
        获取数据对象（包含关联的 connection 和 uploaded_file）

        Args:
            raw_data_id: 数据对象 ID
            user_id: 用户 ID

        Returns:
            数据对象实例

        Raises:
            NotFoundException: 数据对象不存在
        """
        raw_data = await self.repo.get_with_relations(raw_data_id)
        if not raw_data or raw_data.user_id != user_id:
            raise NotFoundException(msg="数据对象不存在")
        return raw_data

    async def get_raw_data_list(
        self,
        user_id: uuid.UUID,
        query_params: RawDataListQuery,
        page_num: int = 1,
        page_size: int = 10,
    ) -> tuple[list[RawData], int]:
        """
        获取数据对象列表

        Args:
            user_id: 用户 ID
            query_params: 查询参数
            page_num: 页码
            page_size: 每页数量

        Returns:
            (数据对象列表, 总数) 元组
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

    async def create_raw_data(self, user_id: uuid.UUID, data: RawDataCreate) -> RawData:
        """
        创建数据对象

        Args:
            user_id: 用户 ID
            data: 创建数据

        Returns:
            创建的数据对象实例

        Raises:
            BadRequestException: 数据验证失败
        """
        # 检查名称是否已存在
        if await self.repo.name_exists(data.name, user_id):
            raise BadRequestException(msg="数据对象名称已存在")

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

            # 自动从 UploadedFile 同步列信息
            if file.columns_info:
                # 转换 columns_info 格式为 columns_schema 格式
                columns_schema = []
                for col in file.columns_info:
                    columns_schema.append(
                        {
                            "name": col.get("name", ""),
                            "data_type": col.get("dtype", col.get("type", "unknown")),
                            "nullable": col.get("nullable", True),
                        }
                    )
                create_data["columns_schema"] = columns_schema
                create_data["status"] = "ready"
                create_data["row_count_estimate"] = file.row_count

        return await self.repo.create(create_data)

    async def update_raw_data(
        self,
        raw_data_id: uuid.UUID,
        user_id: uuid.UUID,
        data: RawDataUpdate,
    ) -> RawData:
        """
        更新数据对象

        Args:
            raw_data_id: 数据对象 ID
            user_id: 用户 ID
            data: 更新数据

        Returns:
            更新后的数据对象实例

        Raises:
            NotFoundException: 数据对象不存在
            BadRequestException: 数据验证失败
        """
        raw_data = await self.get_raw_data(raw_data_id, user_id)

        # 检查名称是否已存在
        if data.name and await self.repo.name_exists(data.name, user_id, exclude_id=raw_data_id):
            raise BadRequestException(msg="数据对象名称已存在")

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
        raw_data_id: uuid.UUID,
        user_id: uuid.UUID,
        data: RawDataColumnUpdate,
    ) -> RawData:
        """
        更新列结构（用户修正类型）

        Args:
            raw_data_id: 数据对象 ID
            user_id: 用户 ID
            data: 列结构数据

        Returns:
            更新后的数据对象实例
        """
        raw_data = await self.get_raw_data(raw_data_id, user_id)

        columns_schema = [col.model_dump() for col in data.columns]

        return await self.repo.update(raw_data, {"columns_schema": columns_schema})

    async def update_sync_status(
        self,
        raw_data_id: uuid.UUID,
        user_id: uuid.UUID,
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
            raw_data_id: 数据对象 ID
            user_id: 用户 ID
            status: 状态
            columns_schema: 列结构
            sample_data: 抽样数据
            row_count_estimate: 估算行数
            error_message: 错误信息

        Returns:
            更新后的数据对象实例
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

    async def delete_raw_data(self, raw_data_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        删除数据对象

        Args:
            raw_data_id: 数据对象 ID
            user_id: 用户 ID

        Raises:
            NotFoundException: 数据对象不存在
        """
        # 验证权限
        await self.get_raw_data(raw_data_id, user_id)

        # 检查是否有 DataSource 引用此 RawData
        if await self.mapping_repo.exists_by_raw_data(raw_data_id):
            raise BadRequestException(msg="有数据源正在使用该数据对象，请先解除映射后再删除")

        success = await self.repo.delete(raw_data_id, soft_delete=True)
        if not success:
            raise NotFoundException(msg="数据对象不存在")

    async def get_raw_data_by_ids(self, ids: list[uuid.UUID], user_id: uuid.UUID) -> list[RawData]:
        """
        根据 ID 列表获取数据对象

        Args:
            ids: ID 列表
            user_id: 用户 ID

        Returns:
            数据对象列表
        """
        return await self.repo.get_by_ids(ids, user_id)

    async def batch_create_from_connection(
        self,
        user_id: uuid.UUID,
        connection_id: uuid.UUID,
        tables: list[dict[str, Any]],
        name_prefix: str | None = None,
        auto_sync: bool = True,
    ) -> list[dict[str, Any]]:
        """
        从数据库连接批量创建数据对象

        Args:
            user_id: 用户 ID
            connection_id: 数据库连接 ID
            tables: 表列表 [{schema_name, table_name, custom_name}]
            name_prefix: 名称前缀
            auto_sync: 是否自动同步

        Returns:
            创建结果列表 [{raw_data_id, name, table_name, status, error_message}]
        """
        # 验证连接是否存在
        connection = await self.connection_repo.get_by_id(connection_id)
        if not connection or connection.user_id != user_id:
            raise BadRequestException(msg="数据库连接不存在")

        results: list[dict[str, Any]] = []

        for table in tables:
            schema_name = table.get("schema_name")
            table_name = table.get("table_name", "")
            custom_name = table.get("custom_name")

            # 生成名称
            if custom_name:
                name = custom_name
            elif name_prefix:
                name = f"{name_prefix}_{table_name}"
            else:
                # 默认名称: connection_name.schema.table 或 connection_name.table
                if schema_name:
                    name = f"{connection.name}.{schema_name}.{table_name}"
                else:
                    name = f"{connection.name}.{table_name}"

            try:
                # 检查名称是否已存在
                if await self.repo.name_exists(name, user_id):
                    # 名称冲突，添加时间戳后缀
                    name = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

                # 创建数据对象
                create_data: dict[str, Any] = {
                    "name": name,
                    "description": f"从 {connection.name} 导入的 {table_name} 表",
                    "raw_type": RawDataType.DATABASE_TABLE.value,
                    "user_id": user_id,
                    "connection_id": connection_id,
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "status": "pending",
                }

                raw_data = await self.repo.create(create_data)

                result: dict[str, Any] = {
                    "raw_data_id": raw_data.id,
                    "name": name,
                    "table_name": table_name,
                    "status": "created",
                    "error_message": None,
                }

                # 自动同步列信息
                if auto_sync:
                    try:
                        await self._sync_database_table(raw_data, connection)
                        result["status"] = "ready"
                    except Exception as sync_err:
                        result["status"] = "error"
                        result["error_message"] = f"同步失败: {sync_err}"
                        # 更新数据对象状态
                        await self.repo.update(
                            raw_data,
                            {"status": "error", "error_message": str(sync_err)},
                        )

                results.append(result)

            except Exception as e:
                results.append(
                    {
                        "raw_data_id": None,
                        "name": name,
                        "table_name": table_name,
                        "status": "error",
                        "error_message": str(e),
                    }
                )

        return results

    async def _sync_database_table(self, raw_data: RawData, connection: Any) -> None:
        """
        同步数据库表的列信息

        Args:
            raw_data: 数据对象实例
            connection: 数据库连接实例
        """
        from app.services.db_connector import DBConnectorService

        # 获取表 Schema
        connector = DBConnectorService()
        schema_info = await connector.get_table_schema(
            connection,
            schema_name=raw_data.schema_name,
            table_name=raw_data.table_name,
        )

        columns_schema = schema_info.get("columns", [])
        row_count = schema_info.get("row_count")

        # 更新数据对象
        await self.repo.update(
            raw_data,
            {
                "status": "ready",
                "columns_schema": columns_schema,
                "row_count_estimate": row_count,
                "synced_at": datetime.now().isoformat(),
            },
        )
