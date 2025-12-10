"""
任务推荐 API 路由
"""

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DBSession
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.models.recommendation import RecommendationStatus
from app.repositories.recommendation import TaskRecommendationRepository
from app.schemas.recommendation import (
    GenerateFollowupRequest,
    GenerateRecommendationsRequest,
    TaskRecommendationResponse,
    TaskRecommendationUpdate,
)
from app.services.recommend import RecommendService
from app.services.session import AnalysisSessionService

router = APIRouter(prefix="/sessions/{session_id}/recommendations", tags=["recommendations"])


@router.get("", response_model=BaseResponse[PageResponse[TaskRecommendationResponse]])
async def get_recommendations(
    session_id: int,
    db: DBSession,
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    status_filter: str | None = None,
    source_type: str | None = None,
):
    """获取会话的推荐列表（分页）"""
    # 验证会话权限
    session_service = AnalysisSessionService(db)
    await session_service.get_session(session_id, current_user.id)

    repo = TaskRecommendationRepository(db)
    items = await repo.get_by_session(
        session_id,
        status=status_filter,
        source_type=source_type,
        skip=page_query.offset,
        limit=page_query.limit,
    )
    total = await repo.count_by_session(
        session_id,
        status=status_filter,
        source_type=source_type,
    )

    response_items = [TaskRecommendationResponse.model_validate(item) for item in items]

    return BaseResponse(
        success=True,
        code=200,
        msg="获取推荐列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=total,
            items=response_items,
        ),
    )


@router.post("", response_model=BaseResponse[list[TaskRecommendationResponse]], status_code=status.HTTP_201_CREATED)
async def generate_recommendations(
    session_id: int,
    db: DBSession,
    current_user: CurrentUser,
    data: GenerateRecommendationsRequest | None = None,
):
    """
    生成初始任务推荐

    基于会话关联的数据源 Schema 生成分析任务推荐
    """
    if data is None:
        data = GenerateRecommendationsRequest()

    # 验证会话权限并获取会话信息
    session_service = AnalysisSessionService(db)
    session, data_source = await session_service.get_session_with_data_source(session_id, current_user.id)

    repo = TaskRecommendationRepository(db)

    # 如果强制重新生成，清理所有现有的 pending 推荐（包括 initial 和 followup）
    if data.force_regenerate:
        await repo.delete_by_session(session_id)  # 删除所有类型

    # 生成推荐
    recommend_service = RecommendService(db)
    recommendation_items = await recommend_service.generate_initial_recommendations(
        session=session,
        data_source=data_source,
        max_count=data.max_count,
    )

    # 保存推荐到数据库
    created = await repo.create_from_items(
        session_id=session_id,
        items=[item.model_dump() for item in recommendation_items],
        user_id=current_user.id,
    )

    response_items = [TaskRecommendationResponse.model_validate(item) for item in created]

    return BaseResponse(
        success=True,
        code=201,
        msg=f"成功生成 {len(created)} 条推荐",
        data=response_items,
    )


@router.post(
    "/followup",
    response_model=BaseResponse[list[TaskRecommendationResponse]],
    status_code=status.HTTP_201_CREATED,
)
async def generate_followup_recommendations(
    session_id: int,
    data: GenerateFollowupRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """
    生成追问推荐

    基于对话上下文生成追问建议
    """
    # 验证会话权限并获取会话信息
    session_service = AnalysisSessionService(db)
    session, data_source = await session_service.get_session_with_data_source(session_id, current_user.id)

    repo = TaskRecommendationRepository(db)

    # 先删除旧的 followup 推荐，避免累积
    await repo.delete_by_session(session_id, source_type="follow_up")

    # 生成追问推荐
    recommend_service = RecommendService(db)
    recommendation_items = await recommend_service.generate_followup_recommendations(
        session=session,
        data_source=data_source,
        conversation_context=data.conversation_context,
        last_result=data.last_result,
        max_count=data.max_count,
    )

    # 保存推荐到数据库
    created = await repo.create_from_items(
        session_id=session_id,
        items=[item.model_dump() for item in recommendation_items],
        user_id=current_user.id,
        trigger_message_id=data.trigger_message_id,
    )

    response_items = [TaskRecommendationResponse.model_validate(item) for item in created]

    return BaseResponse(
        success=True,
        code=201,
        msg=f"成功生成 {len(created)} 条追问推荐",
        data=response_items,
    )


@router.put("/{recommendation_id}", response_model=BaseResponse[TaskRecommendationResponse])
async def update_recommendation(
    session_id: int,
    recommendation_id: int,
    data: TaskRecommendationUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """更新推荐状态"""
    # 验证会话权限
    session_service = AnalysisSessionService(db)
    await session_service.get_session(session_id, current_user.id)

    # 验证状态值
    try:
        status_enum = RecommendationStatus(data.status)
    except ValueError as e:
        raise BadRequestException(msg=f"无效的状态值: {data.status}") from e

    repo = TaskRecommendationRepository(db)

    # 获取并验证推荐归属
    recommendation = await repo.get_by_id(recommendation_id)
    if not recommendation or recommendation.session_id != session_id:
        raise NotFoundException(msg="推荐不存在")

    # 更新状态
    updated = await repo.update_status(recommendation_id, status_enum)
    if not updated:
        raise NotFoundException(msg="推荐不存在")

    return BaseResponse(
        success=True,
        code=200,
        msg="更新推荐状态成功",
        data=TaskRecommendationResponse.model_validate(updated),
    )


@router.delete("", response_model=BaseResponse[None])
async def dismiss_all_recommendations(
    session_id: int,
    db: DBSession,
    current_user: CurrentUser,
    source_type: str | None = None,
):
    """批量忽略会话中的待选择推荐"""
    # 验证会话权限
    session_service = AnalysisSessionService(db)
    await session_service.get_session(session_id, current_user.id)

    repo = TaskRecommendationRepository(db)
    count = await repo.dismiss_by_session(session_id, source_type=source_type)

    return BaseResponse(
        success=True,
        code=200,
        msg=f"已忽略 {count} 条推荐",
        data=None,
    )
