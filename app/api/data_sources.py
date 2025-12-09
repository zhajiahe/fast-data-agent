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
    RawMappingResponse,
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

    # 获取数据源
    service = DataSourceService(db)
    data_source = await service.get_data_source_with_mappings(data_source_id, current_user.id)

    if not data_source.target_fields:
        raise BadRequestException(msg="数据源未定义目标字段")

    if not data_source.raw_mappings:
        raise BadRequestException(msg="数据源未配置原始数据映射")

    # TODO: 实现合并预览逻辑
    # 1. 遍历每个 raw_mapping
    # 2. 从对应的 RawData 获取数据
    # 3. 根据 field_mappings 进行字段转换
    # 4. 合并所有数据

    # 暂时返回空数据
    columns = [TargetField.model_validate(f) for f in data_source.target_fields]

    return BaseResponse(
        success=True,
        code=200,
        msg="预览成功",
        data=DataSourcePreviewResponse(
            columns=columns,
            rows=[],
            source_stats={},
            preview_at=datetime.now().isoformat(),
        ),
    )
