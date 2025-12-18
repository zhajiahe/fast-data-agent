"""
分析会话服务

处理分析会话相关的业务逻辑
"""

import uuid
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.session import AnalysisSession
from app.repositories.session import AnalysisSessionRepository
from app.schemas.session import (
    AnalysisSessionCreate,
    AnalysisSessionListQuery,
    AnalysisSessionUpdate,
)
from app.services.data_source import DataSourceService


class AnalysisSessionService:
    """分析会话服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnalysisSessionRepository(db)
        self.data_source_service = DataSourceService(db)

    async def get_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> AnalysisSession:
        """
        获取单个会话

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            会话实例

        Raises:
            NotFoundException: 会话不存在
        """
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise NotFoundException(msg="会话不存在")
        return session

    async def get_sessions(
        self,
        user_id: uuid.UUID,
        query_params: AnalysisSessionListQuery,
        page_num: int = 1,
        page_size: int = 10,
    ) -> tuple[list[AnalysisSession], int]:
        """
        获取会话列表

        Args:
            user_id: 用户 ID
            query_params: 查询参数
            page_num: 页码
            page_size: 每页数量

        Returns:
            (会话列表, 总数) 元组
        """
        skip = (page_num - 1) * page_size
        return await self.repo.search(
            user_id,
            keyword=query_params.keyword,
            status=query_params.status,
            skip=skip,
            limit=page_size,
        )

    async def create_session(
        self,
        user_id: uuid.UUID,
        data: AnalysisSessionCreate,
        *,
        generate_recommendations: bool = True,
    ) -> AnalysisSession:
        """
        创建会话

        Args:
            user_id: 用户 ID
            data: 创建数据
            generate_recommendations: 是否自动生成初始推荐

        Returns:
            创建的会话实例

        Raises:
            BadRequestException: 数据验证失败
        """
        # 验证数据源是否存在且属于当前用户
        data_source = None
        if data.data_source_id is not None:
            data_sources = await self.data_source_service.get_data_sources_by_ids([data.data_source_id], user_id)
            if len(data_sources) != 1:
                raise BadRequestException(msg="数据源不存在或无权访问")
            data_source = data_sources[0]

        # 创建会话
        create_data: dict[str, Any] = {
            "name": data.name,
            "description": data.description,
            "user_id": user_id,
            "data_source_id": data.data_source_id,
            "config": data.config,
            "status": "active",
            "message_count": 0,
        }

        session = await self.repo.create(create_data)

        # 初始化沙盒中的 DuckDB 文件
        await self._init_session_duckdb(user_id, session.id, data_source)

        return session

    async def _init_session_duckdb(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        data_source: Any | None,
    ) -> None:
        """
        初始化会话的 DuckDB 文件

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            data_source: 数据源（可选）
        """
        from app.utils.tools import get_sandbox_client

        try:
            client = get_sandbox_client()

            # 构建初始化请求
            init_request: dict[str, Any] = {}

            if data_source:
                # 获取数据源的 RawData 列表
                raw_data_list = await self._build_raw_data_configs(data_source)

                # 构建字段映射配置（含自动生成默认映射）
                raw_mappings = self._build_raw_mappings(data_source)

                # 获取 target_fields，如果未定义则自动生成
                target_fields = data_source.target_fields
                if not target_fields and raw_mappings:
                    # 从第一个 RawData 的 columns_schema 自动生成 target_fields
                    first_mapping = raw_mappings[0]
                    target_fields = [
                        {"name": col_name, "data_type": "unknown"}
                        for col_name in first_mapping.get("mappings", {}).keys()
                    ]

                init_request = {
                    "data_source": {
                        "id": str(data_source.id),  # UUID 转为字符串
                        "name": data_source.name,
                        "raw_data_list": raw_data_list,
                        "target_fields": target_fields,
                        "raw_mappings": raw_mappings,
                    }
                }

            # 调用沙盒 API 初始化 DuckDB
            response = await client.post(
                "/init_session",
                params={"user_id": str(user_id), "thread_id": str(session_id)},
                json=init_request,
            )

            result = response.json()
            if not result.get("success"):
                logger.warning(f"Failed to init session DuckDB: {result}")
            else:
                logger.info(
                    f"Session DuckDB initialized: session_id={session_id}, views={result.get('views_created', [])}"
                )

        except Exception as e:
            # 初始化 DuckDB 失败不影响会话创建
            logger.warning(f"Failed to init session DuckDB: {e}")

    async def _build_raw_data_configs(self, data_source: Any) -> list[dict[str, Any]]:
        """
        构建 RawData 配置列表

        Args:
            data_source: 数据源

        Returns:
            RawData 配置列表
        """
        from app.repositories.raw_data import RawDataRepository

        raw_data_configs: list[dict[str, Any]] = []
        raw_data_repo = RawDataRepository(self.db)

        # 获取数据源关联的 RawData
        if not data_source.raw_mappings:
            return raw_data_configs

        for mapping in data_source.raw_mappings:
            if not mapping.is_enabled:
                continue

            raw_data = await raw_data_repo.get_by_id(mapping.raw_data_id)
            if not raw_data:
                continue

            config: dict[str, Any] = {
                "id": str(raw_data.id),  # UUID 转为字符串
                "name": raw_data.name,
                "raw_type": raw_data.raw_type,
            }

            if raw_data.raw_type == "database_table":
                # 数据库表类型：需要获取连接信息
                if raw_data.connection:
                    from app.core.encryption import decrypt_str

                    conn = raw_data.connection
                    config.update(
                        {
                            "db_type": conn.db_type,
                            "host": conn.host,
                            "port": conn.port,
                            "database": conn.database,
                            "username": conn.username,
                            "password": decrypt_str(conn.password, allow_plaintext=True),  # 解密密码
                            "schema_name": raw_data.schema_name,
                            "table_name": raw_data.table_name,
                            "custom_sql": raw_data.custom_sql,
                        }
                    )

            elif raw_data.raw_type == "file":
                # 文件类型：需要获取 MinIO 信息
                if raw_data.uploaded_file:
                    file = raw_data.uploaded_file
                    config.update(
                        {
                            "file_type": file.file_type,
                            "object_key": file.object_key,
                            "bucket_name": file.bucket_name or "data-agent",
                        }
                    )

            raw_data_configs.append(config)

        return raw_data_configs

    def _build_raw_mappings(self, data_source: Any) -> list[dict[str, Any]]:
        """
        构建字段映射配置列表（含自动生成默认映射）

        Args:
            data_source: 数据源

        Returns:
            字段映射配置列表: [{raw_data_id, raw_data_name, mappings}]

        自动映射逻辑：
        - 如果没有定义 field_mappings，自动生成恒等映射（column_name → column_name）
        - 基于 RawData 的 columns_schema 生成
        """
        raw_mappings: list[dict[str, Any]] = []

        if not data_source.raw_mappings:
            return raw_mappings

        for mapping in data_source.raw_mappings:
            if not mapping.is_enabled or not mapping.raw_data:
                continue

            raw = mapping.raw_data

            # 优先使用用户定义的 field_mappings
            if mapping.field_mappings:
                raw_mappings.append(
                    {
                        "raw_data_id": str(mapping.raw_data_id),  # UUID 转为字符串
                        "raw_data_name": raw.name,
                        "mappings": mapping.field_mappings,
                    }
                )
            # 自动生成恒等映射：column_name → column_name
            elif raw.columns_schema:
                auto_mappings = {}
                for col in raw.columns_schema:
                    col_name = col.get("name", "")
                    if col_name:
                        auto_mappings[col_name] = col_name  # 恒等映射
                if auto_mappings:
                    raw_mappings.append(
                        {
                            "raw_data_id": str(mapping.raw_data_id),  # UUID 转为字符串
                            "raw_data_name": raw.name,
                            "mappings": auto_mappings,
                        }
                    )

        return raw_mappings

    async def update_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        data: AnalysisSessionUpdate,
    ) -> AnalysisSession:
        """
        更新会话

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            data: 更新数据

        Returns:
            更新后的会话实例

        Raises:
            NotFoundException: 会话不存在
            BadRequestException: 数据验证失败
        """
        session = await self.get_session(session_id, user_id)

        # 构建更新数据
        update_data: dict[str, Any] = {}
        data_source_changed = False
        new_data_source = None

        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description

        # 如果更新数据源，验证数据源
        if data.data_source_id is not None:
            data_sources = await self.data_source_service.get_data_sources_by_ids([data.data_source_id], user_id)
            if len(data_sources) != 1:
                raise BadRequestException(msg="数据源不存在或无权访问")
            update_data["data_source_id"] = data.data_source_id
            data_source_changed = True
            new_data_source = data_sources[0]

        if data.config is not None:
            update_data["config"] = data.config

        if update_data:
            session = await self.repo.update(session, update_data)

        # 如果数据源变更，重新初始化 DuckDB
        if data_source_changed:
            await self._init_session_duckdb(user_id, session_id, new_data_source)

        return session

    async def delete_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        删除会话

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Raises:
            NotFoundException: 会话不存在
        """
        # 验证权限
        await self.get_session(session_id, user_id)

        success = await self.repo.delete(session_id, soft_delete=True)
        if not success:
            raise NotFoundException(msg="会话不存在")

    async def archive_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> AnalysisSession:
        """
        归档会话

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            更新后的会话实例
        """
        session = await self.get_session(session_id, user_id)
        return await self.repo.update(session, {"status": "archived"})

    async def get_session_with_data_source(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> tuple[AnalysisSession, Any | None]:
        """
        获取会话及其关联的数据源

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            (会话实例, 数据源或 None)
        """
        session = await self.get_session(session_id, user_id)

        data_source = None
        if session.data_source_id:
            data_sources = await self.data_source_service.get_data_sources_by_ids([session.data_source_id], user_id)
            if data_sources:
                data_source = data_sources[0]

        return session, data_source
