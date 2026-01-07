"""
分析会话服务

处理分析会话相关的业务逻辑
"""

import uuid
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_str
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.raw_data import RawData
from app.models.session import AnalysisSession, SessionRawData
from app.repositories.raw_data import RawDataRepository
from app.repositories.session import AnalysisSessionRepository
from app.schemas.session import (
    AnalysisSessionCreate,
    AnalysisSessionListQuery,
    AnalysisSessionUpdate,
)


class AnalysisSessionService:
    """分析会话服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AnalysisSessionRepository(db)
        self.raw_data_repo = RawDataRepository(db)

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
    ) -> AnalysisSession:
        """
        创建会话

        Args:
            user_id: 用户 ID
            data: 创建数据

        Returns:
            创建的会话实例

        Raises:
            BadRequestException: 数据验证失败
        """
        # 验证 RawData 存在且属于当前用户
        raw_data_list = await self.raw_data_repo.get_by_ids_with_relations(data.raw_data_ids, user_id)
        if len(raw_data_list) != len(data.raw_data_ids):
            raise BadRequestException(msg="部分数据对象不存在或无权访问")

        # 创建会话
        create_data: dict[str, Any] = {
            "name": data.name,
            "description": data.description,
            "user_id": user_id,
            "config": data.config,
            "status": "active",
            "message_count": 0,
        }

        session = await self.repo.create(create_data)

        # 创建 SessionRawData 关联
        for raw_data in raw_data_list:
            link = SessionRawData(
                session_id=session.id,
                raw_data_id=raw_data.id,
                alias=raw_data.name,  # 默认用 RawData 名称作为别名
            )
            self.db.add(link)
        await self.db.flush()

        # 初始化沙盒 DuckDB
        await self._init_session_duckdb(user_id, session.id, raw_data_list)

        return session

    async def _init_session_duckdb(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        raw_data_list: list[RawData],
    ) -> None:
        """
        初始化会话的 DuckDB 文件

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            raw_data_list: 数据对象列表
        """
        from app.utils.tools import get_sandbox_client

        if not raw_data_list:
            return

        try:
            client = get_sandbox_client()

            # 构建 RawData 配置列表
            raw_data_configs = self._build_raw_data_configs(raw_data_list)

            response = await client.post(
                "/init_session",
                params={"user_id": str(user_id), "thread_id": str(session_id)},
                json={"raw_data_list": raw_data_configs},
            )

            result = response.json()
            if result.get("success"):
                logger.info(
                    f"Session DuckDB initialized: session_id={session_id}, "
                    f"views={result.get('views_created', [])}"
                )
            else:
                logger.warning(f"Failed to init session DuckDB: {result}")

        except Exception as e:
            logger.warning(f"Failed to init session DuckDB: {e}")

    def _build_raw_data_configs(self, raw_data_list: list[RawData]) -> list[dict[str, Any]]:
        """构建 RawData 配置列表"""
        configs: list[dict[str, Any]] = []

        for raw_data in raw_data_list:
            config: dict[str, Any] = {
                "id": str(raw_data.id),
                "name": raw_data.name,
                "raw_type": raw_data.raw_type,
            }

            if raw_data.raw_type == "database_table" and raw_data.connection:
                conn = raw_data.connection
                config.update(
                    {
                        "db_type": conn.db_type,
                        "host": conn.host,
                        "port": conn.port,
                        "database": conn.database,
                        "username": conn.username,
                        "password": decrypt_str(conn.password, allow_plaintext=True),
                        "schema_name": raw_data.schema_name,
                        "table_name": raw_data.table_name,
                        "custom_sql": raw_data.custom_sql,
                    }
                )

            elif raw_data.raw_type == "file" and raw_data.uploaded_file:
                file = raw_data.uploaded_file
                config.update(
                    {
                        "file_type": file.file_type,
                        "object_key": file.object_key,
                        "bucket_name": file.bucket_name or "data-agent",
                    }
                )

            configs.append(config)

        return configs

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
        raw_data_changed = False
        new_raw_data_list: list[RawData] = []

        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.config is not None:
            update_data["config"] = data.config

        # 如果更新数据对象
        if data.raw_data_ids is not None:
            new_raw_data_list = await self.raw_data_repo.get_by_ids_with_relations(data.raw_data_ids, user_id)
            if len(new_raw_data_list) != len(data.raw_data_ids):
                raise BadRequestException(msg="部分数据对象不存在或无权访问")
            raw_data_changed = True

        if update_data:
            session = await self.repo.update(session, update_data)

        # 如果数据对象变更，重新创建关联
        if raw_data_changed:
            # 删除旧关联
            for link in session.raw_data_links:
                await self.db.delete(link)

            # 创建新关联
            for raw_data in new_raw_data_list:
                link = SessionRawData(
                    session_id=session.id,
                    raw_data_id=raw_data.id,
                    alias=raw_data.name,
                )
                self.db.add(link)
            await self.db.flush()

            # 重新初始化 DuckDB
            await self._init_session_duckdb(user_id, session_id, new_raw_data_list)

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
        from app.utils.tools import get_sandbox_client

        # 验证权限
        await self.get_session(session_id, user_id)

        # 清理沙箱中的会话工作目录
        try:
            client = get_sandbox_client()
            await client.post(
                "/reset/session",
                params={"user_id": str(user_id), "thread_id": str(session_id)},
            )
            logger.info(f"会话沙箱目录已清理: session_id={session_id}")
        except Exception as e:
            # 沙箱清理失败不应阻止会话删除
            logger.warning(f"清理会话沙箱目录失败: session_id={session_id}, error={e}")

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

    async def get_session_with_raw_data(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> tuple[AnalysisSession, list[RawData]]:
        """
        获取会话及其关联的数据对象

        Args:
            session_id: 会话 ID
            user_id: 用户 ID

        Returns:
            (会话实例, 数据对象列表)
        """
        session = await self.get_session(session_id, user_id)

        raw_data_list: list[RawData] = []
        if session.raw_data_links:
            raw_data_ids = [link.raw_data_id for link in session.raw_data_links if link.is_enabled]
            raw_data_list = await self.raw_data_repo.get_by_ids_with_relations(raw_data_ids, user_id)

        return session, raw_data_list
