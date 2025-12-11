"""
数据库连接服务

处理数据库连接管理相关的业务逻辑
"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_str
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.database_connection import DatabaseConnection
from app.repositories.database_connection import DatabaseConnectionRepository
from app.repositories.raw_data import RawDataRepository
from app.schemas.database_connection import (
    DatabaseConnectionCreate,
    DatabaseConnectionUpdate,
)


class DatabaseConnectionService:
    """数据库连接服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DatabaseConnectionRepository(db)
        self.raw_data_repo = RawDataRepository(db)

    async def get_connection(self, connection_id: int, user_id: int) -> DatabaseConnection:
        """
        获取单个数据库连接

        Args:
            connection_id: 连接 ID
            user_id: 用户 ID

        Returns:
            连接实例

        Raises:
            NotFoundException: 连接不存在
        """
        connection = await self.repo.get_by_id(connection_id)
        if not connection or connection.user_id != user_id:
            raise NotFoundException(msg="数据库连接不存在")
        return connection

    async def get_connections(
        self,
        user_id: int,
        *,
        keyword: str | None = None,
        db_type: str | None = None,
        page_num: int = 1,
        page_size: int = 10,
    ) -> tuple[list[DatabaseConnection], int]:
        """
        获取数据库连接列表

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            db_type: 数据库类型
            page_num: 页码
            page_size: 每页数量

        Returns:
            (连接列表, 总数) 元组
        """
        skip = (page_num - 1) * page_size
        return await self.repo.search(
            user_id,
            keyword=keyword,
            db_type=db_type,
            skip=skip,
            limit=page_size,
        )

    async def create_connection(
        self,
        user_id: int,
        data: DatabaseConnectionCreate,
        *,
        auto_create_raw_data: bool = True,
        auto_sync_raw_data: bool = True,
        max_auto_tables: int = 20,
    ) -> tuple[DatabaseConnection, list[dict[str, Any]] | None, str | None]:
        """
        创建数据库连接

        Args:
            user_id: 用户 ID
            data: 创建数据
            auto_create_raw_data: 创建连接后是否自动为数据库表生成 RawData
            auto_sync_raw_data: 自动创建的 RawData 是否同步列信息
            max_auto_tables: 自动创建 RawData 时的最大表数量（避免一次性创建过多）

        Returns:
            (连接实例, 自动创建结果列表, 错误信息)

        Raises:
            BadRequestException: 数据验证失败
        """
        # 检查名称是否已存在
        if await self.repo.name_exists(data.name, user_id):
            raise BadRequestException(msg="连接名称已存在")

        # 构建创建数据
        create_data: dict[str, Any] = {
            "name": data.name,
            "description": data.description,
            "user_id": user_id,
            "db_type": data.config.db_type.value,
            "host": data.config.host,
            "port": data.config.port,
            "database": data.config.database,
            "username": data.config.username,
            # 加密存储密码
            "password": encrypt_str(data.config.password),
            "extra_params": data.config.extra_params,
        }

        connection = await self.repo.create(create_data)

        # 自动为数据库表创建 RawData（可选）
        auto_results: list[dict[str, Any]] | None = None
        auto_error: str | None = None

        if auto_create_raw_data:
            try:
                # 懒加载依赖，避免循环导入
                from app.services.db_connector import DBConnectorService
                from app.services.raw_data import RawDataService

                connector = DBConnectorService()
                tables = await connector.get_tables(connection)

                # 限制自动创建的表数量，防止一次性创建过多
                if max_auto_tables and max_auto_tables > 0:
                    tables = tables[:max_auto_tables]

                # 转换为批量创建所需的表结构
                table_selections = [
                    {
                        "schema_name": t.get("schema"),
                        "table_name": t.get("name", ""),
                        # 使用 name_prefix 统一命名，不需要 custom_name
                    }
                    for t in tables
                    if t.get("name")
                ]

                if table_selections:
                    raw_service = RawDataService(self.db)
                    auto_results = await raw_service.batch_create_from_connection(
                        user_id=user_id,
                        connection_id=connection.id,
                        tables=table_selections,
                        name_prefix=connection.name,
                        auto_sync=auto_sync_raw_data,
                    )
                else:
                    auto_results = []
            except Exception as e:  # pragma: no cover - 防御性捕获
                auto_error = str(e)

        return connection, auto_results, auto_error

    async def update_connection(
        self,
        connection_id: int,
        user_id: int,
        data: DatabaseConnectionUpdate,
    ) -> DatabaseConnection:
        """
        更新数据库连接

        Args:
            connection_id: 连接 ID
            user_id: 用户 ID
            data: 更新数据

        Returns:
            更新后的连接实例

        Raises:
            NotFoundException: 连接不存在
            BadRequestException: 数据验证失败
        """
        connection = await self.get_connection(connection_id, user_id)

        # 检查名称是否已存在
        if data.name and await self.repo.name_exists(data.name, user_id, exclude_id=connection_id):
            raise BadRequestException(msg="连接名称已存在")

        # 构建更新数据
        update_data: dict[str, Any] = {}

        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description

        # 连接配置更新
        if data.config:
            update_data.update(
                {
                    "db_type": data.config.db_type.value,
                    "host": data.config.host,
                    "port": data.config.port,
                    "database": data.config.database,
                    "username": data.config.username,
                    "password": encrypt_str(data.config.password),
                    "extra_params": data.config.extra_params,
                }
            )

        if update_data:
            connection = await self.repo.update(connection, update_data)

        return connection

    async def delete_connection(self, connection_id: int, user_id: int) -> None:
        """
        删除数据库连接

        Args:
            connection_id: 连接 ID
            user_id: 用户 ID

        Raises:
            NotFoundException: 连接不存在
        """
        # 验证权限
        await self.get_connection(connection_id, user_id)

        # 检查是否有 RawData 引用此连接
        if await self.raw_data_repo.exists_by_connection(connection_id, user_id):
            raise BadRequestException(msg="存在使用该连接的数据对象，请先解绑后再删除")

        success = await self.repo.delete(connection_id, soft_delete=True)
        if not success:
            raise NotFoundException(msg="数据库连接不存在")

    async def update_test_status(
        self,
        connection_id: int,
        user_id: int,
        *,
        is_active: bool,
    ) -> DatabaseConnection:
        """
        更新连接测试状态

        Args:
            connection_id: 连接 ID
            user_id: 用户 ID
            is_active: 是否可用

        Returns:
            更新后的连接实例
        """
        connection = await self.get_connection(connection_id, user_id)

        update_data = {
            "is_active": is_active,
            "last_tested_at": datetime.now().isoformat(),
        }

        return await self.repo.update(connection, update_data)
