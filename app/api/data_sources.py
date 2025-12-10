"""
数据源管理 API 路由
"""

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceListQuery,
    DataSourcePreviewRequest,
    DataSourcePreviewResponse,
    DataSourceResponse,
    DataSourceUpdate,
    FieldMappingSuggestionResponse,
    RawMappingResponse,
    SuggestedTargetField,
    SuggestMappingsRequest,
    SuggestMappingsResponse,
    SuggestTargetFieldsRequest,
    SuggestTargetFieldsResponse,
    TargetField,
)
from app.services.data_source import DataSourceService

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


def _build_response(data_source, include_mappings: bool = False) -> DataSourceResponse:
    """构建数据源响应"""
    raw_mappings = None
    if include_mappings and data_source.raw_mappings:
        raw_mappings = [
            RawMappingResponse(
                id=m.id,
                raw_data_id=m.raw_data_id,
                raw_data_name=m.raw_data.name if m.raw_data else None,
                field_mappings=m.field_mappings,
                priority=m.priority,
                is_enabled=m.is_enabled,
            )
            for m in data_source.raw_mappings
        ]

    target_fields = None
    if data_source.target_fields:
        target_fields = [TargetField.model_validate(f) for f in data_source.target_fields]

    return DataSourceResponse(
        id=data_source.id,
        user_id=data_source.user_id,
        name=data_source.name,
        description=data_source.description,
        category=data_source.category,
        target_fields=target_fields,
        schema_cache=data_source.schema_cache,
        raw_mappings=raw_mappings,
        create_time=data_source.create_time,
        update_time=data_source.update_time,
    )


@router.get("", response_model=BaseResponse[PageResponse[DataSourceResponse]])
async def get_data_sources(
    db: DBSession,
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    query_params: DataSourceListQuery = Depends(),
):
    """获取数据源列表（分页）"""
    service = DataSourceService(db)
    items, total = await service.get_data_sources(
        user_id=current_user.id,
        query_params=query_params,
        page_num=page_query.page_num,
        page_size=page_query.page_size,
    )
    data_list = [_build_response(item) for item in items]
    return BaseResponse(
        success=True,
        code=200,
        msg="获取数据源列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=total,
            items=data_list,
        ),
    )


@router.get("/{data_source_id}", response_model=BaseResponse[DataSourceResponse])
async def get_data_source(data_source_id: int, current_user: CurrentUser, db: DBSession):
    """获取单个数据源详情（包含映射信息）"""
    service = DataSourceService(db)
    item = await service.get_data_source_with_mappings(data_source_id, current_user.id)
    return BaseResponse(
        success=True,
        code=200,
        msg="获取数据源成功",
        data=_build_response(item, include_mappings=True),
    )


@router.post("", response_model=BaseResponse[DataSourceResponse], status_code=status.HTTP_201_CREATED)
async def create_data_source(data: DataSourceCreate, current_user: CurrentUser, db: DBSession):
    """创建数据源"""
    service = DataSourceService(db)
    item = await service.create_data_source(current_user.id, data)
    # 重新获取以包含映射关系
    item = await service.get_data_source_with_mappings(item.id, current_user.id)
    return BaseResponse(
        success=True,
        code=201,
        msg="创建数据源成功",
        data=_build_response(item, include_mappings=True),
    )


@router.put("/{data_source_id}", response_model=BaseResponse[DataSourceResponse])
async def update_data_source(
    data_source_id: int,
    data: DataSourceUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """更新数据源"""
    service = DataSourceService(db)
    await service.update_data_source(data_source_id, current_user.id, data)
    # 重新获取以包含映射关系
    item = await service.get_data_source_with_mappings(data_source_id, current_user.id)
    return BaseResponse(
        success=True,
        code=200,
        msg="更新数据源成功",
        data=_build_response(item, include_mappings=True),
    )


@router.delete("/{data_source_id}", response_model=BaseResponse[None])
async def delete_data_source(data_source_id: int, current_user: CurrentUser, db: DBSession):
    """删除数据源"""
    service = DataSourceService(db)
    await service.delete_data_source(data_source_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="删除数据源成功", data=None)


@router.post("/{data_source_id}/preview", response_model=BaseResponse[DataSourcePreviewResponse])
async def preview_data_source(
    data_source_id: int,
    current_user: CurrentUser,
    db: DBSession,
    request: DataSourcePreviewRequest | None = None,
):
    """
    预览数据源（合并后的数据）

    根据字段映射，从各 RawData 获取数据并合并展示
    """
    from datetime import datetime

    from app.core.exceptions import BadRequestException

    if request is None:
        request = DataSourcePreviewRequest()

    service = DataSourceService(db)
    preview_result = await service.preview_data_source(
        data_source_id=data_source_id,
        user_id=current_user.id,
        limit=request.limit,
    )

    return BaseResponse(
        success=True,
        code=200,
        msg="预览成功",
        data=preview_result,
    )


@router.post("/suggest-mappings", response_model=BaseResponse[SuggestMappingsResponse])
async def suggest_field_mappings(
    request: SuggestMappingsRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    智能字段映射建议

    根据目标字段和原始数据的列信息，推荐最佳的字段映射关系。
    基于字段名相似度、同义词匹配和数据类型兼容性进行匹配。
    """
    from app.repositories.raw_data import RawDataRepository
    from app.services.field_mapping import FieldMappingService

    # 获取所有指定的 RawData
    raw_data_repo = RawDataRepository(db)
    raw_data_list = await raw_data_repo.get_by_ids(request.raw_data_ids, current_user.id)

    if not raw_data_list:
        return BaseResponse(
            success=True,
            code=200,
            msg="未找到匹配的原始数据",
            data=SuggestMappingsResponse(suggestions=[]),
        )

    # 构建原始数据源信息
    raw_data_sources = [
        {
            "id": rd.id,
            "name": rd.name,
            "columns_schema": rd.columns_schema,
        }
        for rd in raw_data_list
    ]

    # 构建目标字段信息
    target_fields = [f.model_dump() for f in request.target_fields]

    # 获取建议
    mapping_service = FieldMappingService()
    suggestions = mapping_service.suggest_mappings(target_fields, raw_data_sources)

    return BaseResponse(
        success=True,
        code=200,
        msg="获取字段映射建议成功",
        data=SuggestMappingsResponse(
            suggestions=[
                FieldMappingSuggestionResponse(
                    target_field=s.target_field,
                    source_field=s.source_field,
                    raw_data_id=s.raw_data_id,
                    raw_data_name=s.raw_data_name,
                    confidence=s.confidence,
                    reason=s.reason,
                )
                for s in suggestions
            ]
        ),
    )


@router.post("/suggest-target-fields", response_model=BaseResponse[SuggestTargetFieldsResponse])
async def suggest_target_fields(
    request: SuggestTargetFieldsRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    从原始数据推断目标字段

    分析多个 RawData 的列结构，合并推断出最佳的目标字段定义。
    """
    from app.repositories.raw_data import RawDataRepository
    from app.services.field_mapping import FieldMappingService

    # 获取所有指定的 RawData
    raw_data_repo = RawDataRepository(db)
    raw_data_list = await raw_data_repo.get_by_ids(request.raw_data_ids, current_user.id)

    if not raw_data_list:
        return BaseResponse(
            success=True,
            code=200,
            msg="未找到匹配的原始数据",
            data=SuggestTargetFieldsResponse(fields=[]),
        )

    # 构建原始数据源信息
    raw_data_sources = [
        {
            "id": rd.id,
            "name": rd.name,
            "columns_schema": rd.columns_schema,
        }
        for rd in raw_data_list
    ]

    # 获取推荐的目标字段
    mapping_service = FieldMappingService()
    suggested_fields = mapping_service.suggest_target_fields_from_raw(raw_data_sources)

    return BaseResponse(
        success=True,
        code=200,
        msg="推断目标字段成功",
        data=SuggestTargetFieldsResponse(
            fields=[
                SuggestedTargetField(
                    name=f["name"],
                    data_type=f["data_type"],
                    description=f.get("description"),
                    source_count=f.get("source_count", 1),
                )
                for f in suggested_fields
            ]
        ),
    )


@router.post("/{data_source_id}/refresh-schema", response_model=BaseResponse[DataSourceResponse])
async def refresh_data_source_schema(
    data_source_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    刷新数据源 Schema

    重新从各 RawData 获取列信息并更新 schema_cache
    """
    from app.core.exceptions import NotFoundException

    service = DataSourceService(db)

    # 验证数据源存在
    data_source = await service.get_data_source_with_mappings(data_source_id, current_user.id)
    if not data_source:
        raise NotFoundException(msg="数据源不存在")

    # 刷新 schema
    await service.refresh_schema_cache(data_source_id, current_user.id)

    # 重新获取
    item = await service.get_data_source_with_mappings(data_source_id, current_user.id)

    return BaseResponse(
        success=True,
        code=200,
        msg="刷新 Schema 成功",
        data=_build_response(item, include_mappings=True),
    )
