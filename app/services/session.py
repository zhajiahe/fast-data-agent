"""
分析会话服务

处理分析会话相关的业务逻辑
"""

from typing import Any

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

    async def get_session(self, session_id: int, user_id: int) -> AnalysisSession:
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
        user_id: int,
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
        user_id: int,
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
        data_source_ids: list[int] = []
        if data.data_source_id is not None:
            data_sources = await self.data_source_service.get_data_sources_by_ids([data.data_source_id], user_id)
            if len(data_sources) != 1:
                raise BadRequestException(msg="数据源不存在或无权访问")
            data_source_ids = [data.data_source_id]

        # 创建会话
        create_data: dict[str, Any] = {
            "name": data.name,
            "description": data.description,
            "user_id": user_id,
            "data_source_ids": data_source_ids if data_source_ids else None,
            "config": data.config,
            "status": "active",
            "message_count": 0,
        }

        session = await self.repo.create(create_data)

        return session

    async def update_session(
        self,
        session_id: int,
        user_id: int,
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

        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description

        # 如果更新数据源，验证数据源
        if data.data_source_id is not None:
            data_sources = await self.data_source_service.get_data_sources_by_ids([data.data_source_id], user_id)
            if len(data_sources) != 1:
                raise BadRequestException(msg="数据源不存在或无权访问")
            update_data["data_source_ids"] = [data.data_source_id]
        # 允许清空数据源（设置为 None 时）
        # 注意：需要显式区分 "未提供" 和 "设置为空"
        # 这里使用特殊约定：如果 data_source_id 字段存在但值为 0，表示清空数据源

        if data.config is not None:
            update_data["config"] = data.config

        if update_data:
            session = await self.repo.update(session, update_data)

        return session

    async def delete_session(self, session_id: int, user_id: int) -> None:
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

    async def archive_session(self, session_id: int, user_id: int) -> AnalysisSession:
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
        session_id: int,
        user_id: int,
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
        if session.data_source_ids and len(session.data_source_ids) > 0:
            data_sources = await self.data_source_service.get_data_sources_by_ids(session.data_source_ids[:1], user_id)
            if data_sources:
                data_source = data_sources[0]

        return session, data_source
