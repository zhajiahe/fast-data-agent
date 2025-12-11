"""
数据对象管理 API 路由
"""

import uuid

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas.raw_data import (
    BatchCreateFromConnectionRequest,
    BatchCreateFromConnectionResponse,
    BatchCreateResult,
    RawDataColumnUpdate,
    RawDataCreate,
    RawDataListQuery,
    RawDataPreviewRequest,
    RawDataPreviewResponse,
    RawDataResponse,
    RawDataUpdate,
)
from app.services.raw_data import RawDataService

router = APIRouter(prefix="/raw-data", tags=["raw-data"])


@router.get("", response_model=BaseResponse[PageResponse[RawDataResponse]])
async def get_raw_data_list(
    db: DBSession,
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    query_params: RawDataListQuery = Depends(),
):
    """获取数据对象列表（分页）"""
    service = RawDataService(db)
    items, total = await service.get_raw_data_list(
        user_id=current_user.id,
        query_params=query_params,
        page_num=page_query.page_num,
        page_size=page_query.page_size,
    )
    data_list = [RawDataResponse.model_validate(item) for item in items]
    return BaseResponse(
        success=True,
        code=200,
        msg="获取数据对象列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=total,
            items=data_list,
        ),
    )


@router.get("/{raw_data_id}", response_model=BaseResponse[RawDataResponse])
async def get_raw_data(raw_data_id: uuid.UUID, current_user: CurrentUser, db: DBSession):
    """获取单个数据对象详情"""
    service = RawDataService(db)
    item = await service.get_raw_data_with_relations(raw_data_id, current_user.id)
    return BaseResponse(
        success=True,
        code=200,
        msg="获取数据对象成功",
        data=RawDataResponse.model_validate(item),
    )


@router.post("", response_model=BaseResponse[RawDataResponse], status_code=status.HTTP_201_CREATED)
async def create_raw_data(data: RawDataCreate, current_user: CurrentUser, db: DBSession):
    """创建数据对象"""
    service = RawDataService(db)
    item = await service.create_raw_data(current_user.id, data)
    return BaseResponse(
        success=True,
        code=201,
        msg="创建数据对象成功",
        data=RawDataResponse.model_validate(item),
    )


@router.post(
    "/batch-from-connection",
    response_model=BaseResponse[BatchCreateFromConnectionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def batch_create_raw_data(data: BatchCreateFromConnectionRequest, current_user: CurrentUser, db: DBSession):
    """
    从数据库连接批量创建数据对象

    用户可以一次性从一个数据库连接中选择多个表创建数据对象
    """
    service = RawDataService(db)
    results = await service.batch_create_from_connection(
        user_id=current_user.id,
        connection_id=data.connection_id,
        tables=[t.model_dump() for t in data.tables],
        name_prefix=data.name_prefix,
        auto_sync=data.auto_sync,
    )

    success_count = sum(1 for r in results if r["status"] != "error" or r["raw_data_id"] is not None)
    failed_count = len(results) - success_count

    return BaseResponse(
        success=True,
        code=201,
        msg=f"批量创建数据对象完成，成功 {success_count} 条，失败 {failed_count} 条",
        data=BatchCreateFromConnectionResponse(
            success_count=success_count,
            failed_count=failed_count,
            results=[BatchCreateResult(**r) for r in results],
        ),
    )


@router.put("/{raw_data_id}", response_model=BaseResponse[RawDataResponse])
async def update_raw_data(
    raw_data_id: uuid.UUID,
    data: RawDataUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """更新数据对象"""
    service = RawDataService(db)
    item = await service.update_raw_data(raw_data_id, current_user.id, data)
    return BaseResponse(
        success=True,
        code=200,
        msg="更新数据对象成功",
        data=RawDataResponse.model_validate(item),
    )


@router.delete("/{raw_data_id}", response_model=BaseResponse[None])
async def delete_raw_data(raw_data_id: uuid.UUID, current_user: CurrentUser, db: DBSession):
    """删除数据对象"""
    service = RawDataService(db)
    await service.delete_raw_data(raw_data_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="删除数据对象成功", data=None)


@router.put("/{raw_data_id}/columns", response_model=BaseResponse[RawDataResponse])
async def update_raw_data_columns(
    raw_data_id: uuid.UUID,
    data: RawDataColumnUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """更新数据对象列类型（用户修正）"""
    service = RawDataService(db)
    item = await service.update_columns_schema(raw_data_id, current_user.id, data)
    return BaseResponse(
        success=True,
        code=200,
        msg="更新列类型成功",
        data=RawDataResponse.model_validate(item),
    )


@router.post("/{raw_data_id}/preview", response_model=BaseResponse[RawDataPreviewResponse])
async def preview_raw_data(
    raw_data_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    request: RawDataPreviewRequest | None = None,
):
    """
    预览数据对象（抽样）

    从数据库表或文件中抽样数据，并推断列类型
    """
    from datetime import datetime

    from app.core.exceptions import BadRequestException
    from app.models.raw_data import RawDataType
    from app.schemas.raw_data import ColumnSchema

    if request is None:
        request = RawDataPreviewRequest()

    # 获取数据对象
    service = RawDataService(db)
    raw_data = await service.get_raw_data_with_relations(raw_data_id, current_user.id)

    columns: list[ColumnSchema] = []
    rows: list[dict] = []
    total_rows: int | None = None

    if raw_data.raw_type == RawDataType.DATABASE_TABLE.value:
        # 数据库表类型：通过 DuckDB 或 DB Connector 预览
        from app.services.db_connector import DBConnectorService

        if not raw_data.connection:
            raise BadRequestException(msg="数据库连接不存在")

        connector = DBConnectorService()
        preview_result = await connector.preview_table(
            raw_data.connection,
            schema_name=raw_data.schema_name,
            table_name=raw_data.table_name,
            custom_sql=raw_data.custom_sql,
            limit=request.limit,
        )
        columns = [
            ColumnSchema(
                name=c["name"],
                data_type=c["data_type"],
                nullable=c.get("nullable", True),
            )
            for c in preview_result.get("columns", [])
        ]
        rows = preview_result.get("rows", [])
        total_rows = preview_result.get("total_rows")

    elif raw_data.raw_type == RawDataType.FILE.value:
        # 文件类型：从 UploadedFile 的 columns_info 和 preview_data 获取
        if not raw_data.uploaded_file:
            raise BadRequestException(msg="关联文件不存在")

        uploaded_file = raw_data.uploaded_file
        if uploaded_file.status != "ready":
            raise BadRequestException(msg="文件尚未处理完成")

        # 从 columns_info 构建列信息
        for col_info in uploaded_file.columns_info or []:
            columns.append(
                ColumnSchema(
                    name=col_info.get("name", ""),
                    data_type=col_info.get("dtype", col_info.get("type", "unknown")),
                    nullable=col_info.get("nullable", True),
                )
            )

        # 从 preview_data 获取行
        preview_data = uploaded_file.preview_data or {}

        # 兼容 list/dict 两种格式
        if isinstance(preview_data, dict):
            rows = preview_data.get("rows", [])[: request.limit]
        elif isinstance(preview_data, list):
            rows = preview_data[: request.limit]
            # 如果还没有列定义，尝试从第一行推断
            if rows and not columns:
                first = rows[0]
                if isinstance(first, dict):
                    columns = [
                        ColumnSchema(name=k, data_type="unknown", nullable=True)
                        for k in first.keys()  # type: ignore[arg-type]
                    ]
        else:
            rows = []
        total_rows = uploaded_file.row_count

    else:
        raise BadRequestException(msg=f"不支持的数据对象类型: {raw_data.raw_type}")

    # 更新同步状态
    await service.update_sync_status(
        raw_data_id,
        current_user.id,
        status="ready",
        columns_schema=[c.model_dump() for c in columns],
        sample_data={"columns": [c.name for c in columns], "rows": rows[:10]},
        row_count_estimate=total_rows,
    )

    return BaseResponse(
        success=True,
        code=200,
        msg="预览成功",
        data=RawDataPreviewResponse(
            columns=columns,
            rows=rows,
            total_rows=total_rows,
            preview_at=datetime.now().isoformat(),
        ),
    )


@router.post("/{raw_data_id}/sync", response_model=BaseResponse[RawDataResponse])
async def sync_raw_data(raw_data_id: uuid.UUID, current_user: CurrentUser, db: DBSession):
    """
    同步数据对象 Schema

    从数据源获取最新的列结构信息
    """
    from app.core.exceptions import BadRequestException
    from app.models.raw_data import RawDataType

    # 获取数据对象
    service = RawDataService(db)
    raw_data = await service.get_raw_data_with_relations(raw_data_id, current_user.id)

    # 更新为同步中状态
    await service.update_sync_status(raw_data_id, current_user.id, status="syncing")

    try:
        if raw_data.raw_type == RawDataType.DATABASE_TABLE.value:
            # 数据库表类型
            from app.services.db_connector import DBConnectorService

            if not raw_data.connection:
                raise BadRequestException(msg="数据库连接不存在")

            connector = DBConnectorService()
            schema_info = await connector.get_table_schema(
                raw_data.connection,
                schema_name=raw_data.schema_name,
                table_name=raw_data.table_name,
            )
            columns_schema = schema_info.get("columns", [])
            row_count = schema_info.get("row_count")

        elif raw_data.raw_type == RawDataType.FILE.value:
            # 文件类型
            if not raw_data.uploaded_file:
                raise BadRequestException(msg="关联文件不存在")

            uploaded_file = raw_data.uploaded_file
            columns_schema = uploaded_file.columns_info or []
            row_count = uploaded_file.row_count

        else:
            raise BadRequestException(msg=f"不支持的数据对象类型: {raw_data.raw_type}")

        # 更新成功状态
        item = await service.update_sync_status(
            raw_data_id,
            current_user.id,
            status="ready",
            columns_schema=columns_schema,
            row_count_estimate=row_count,
        )

    except Exception as e:
        # 更新错误状态
        item = await service.update_sync_status(
            raw_data_id,
            current_user.id,
            status="error",
            error_message=str(e),
        )

    return BaseResponse(
        success=True,
        code=200,
        msg="同步完成",
        data=RawDataResponse.model_validate(item),
    )
