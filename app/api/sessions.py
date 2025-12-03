"""
分析会话 API 路由
"""

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas.analysis_session import (
    AnalysisSessionCreate,
    AnalysisSessionDetail,
    AnalysisSessionListQuery,
    AnalysisSessionResponse,
    AnalysisSessionUpdate,
)
from app.schemas.data_source import DataSourceResponse
from app.services.analysis_session import AnalysisSessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=BaseResponse[PageResponse[AnalysisSessionResponse]])
async def get_sessions(
    db: DBSession,
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    query_params: AnalysisSessionListQuery = Depends(),
):
    """获取会话列表（分页）"""
    service = AnalysisSessionService(db)
    items, total = await service.get_sessions(
        user_id=current_user.id,
        query_params=query_params,
        page_num=page_query.page_num,
        page_size=page_query.page_size,
    )
    data_list = [AnalysisSessionResponse.model_validate(item) for item in items]
    return BaseResponse(
        success=True,
        code=200,
        msg="获取会话列表成功",
        data=PageResponse(page_num=page_query.page_num, page_size=page_query.page_size, total=total, items=data_list),
    )


@router.get("/{session_id}", response_model=BaseResponse[AnalysisSessionDetail])
async def get_session(session_id: int, current_user: CurrentUser, db: DBSession):
    """获取单个会话详情（包含数据源信息）"""
    service = AnalysisSessionService(db)
    session, data_sources = await service.get_session_with_data_sources(session_id, current_user.id)

    # 构建响应
    response = AnalysisSessionDetail(
        id=session.id,
        user_id=session.user_id,
        name=session.name,
        description=session.description,
        data_source_ids=session.data_source_ids,
        config=session.config,
        status=session.status,
        message_count=session.message_count,
        create_time=session.create_time,
        update_time=session.update_time,
        data_sources=[DataSourceResponse.model_validate(ds) for ds in data_sources],
    )

    return BaseResponse(success=True, code=200, msg="获取会话成功", data=response)


@router.post("", response_model=BaseResponse[AnalysisSessionResponse], status_code=status.HTTP_201_CREATED)
async def create_session(data: AnalysisSessionCreate, current_user: CurrentUser, db: DBSession):
    """创建会话"""
    service = AnalysisSessionService(db)
    item = await service.create_session(current_user.id, data)
    return BaseResponse(success=True, code=201, msg="创建会话成功", data=AnalysisSessionResponse.model_validate(item))


@router.put("/{session_id}", response_model=BaseResponse[AnalysisSessionResponse])
async def update_session(
    session_id: int,
    data: AnalysisSessionUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """更新会话"""
    service = AnalysisSessionService(db)
    item = await service.update_session(session_id, current_user.id, data)
    return BaseResponse(success=True, code=200, msg="更新会话成功", data=AnalysisSessionResponse.model_validate(item))


@router.delete("/{session_id}", response_model=BaseResponse[None])
async def delete_session(session_id: int, current_user: CurrentUser, db: DBSession):
    """删除会话"""
    service = AnalysisSessionService(db)
    await service.delete_session(session_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="删除会话成功", data=None)


@router.post("/{session_id}/archive", response_model=BaseResponse[AnalysisSessionResponse])
async def archive_session(session_id: int, current_user: CurrentUser, db: DBSession):
    """归档会话"""
    service = AnalysisSessionService(db)
    item = await service.archive_session(session_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="会话已归档", data=AnalysisSessionResponse.model_validate(item))
