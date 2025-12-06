"""
数据源管理 API 路由
"""

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceListQuery,
    DataSourceResponse,
    DataSourceSchemaResponse,
    DataSourceTestResult,
    DataSourceUpdate,
)
from app.services.data_source import DataSourceService

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


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
    data_list = [DataSourceResponse.model_validate(item) for item in items]
    return BaseResponse(
        success=True,
        code=200,
        msg="获取数据源列表成功",
        data=PageResponse(page_num=page_query.page_num, page_size=page_query.page_size, total=total, items=data_list),
    )


@router.get("/{data_source_id}", response_model=BaseResponse[DataSourceResponse])
async def get_data_source(data_source_id: int, current_user: CurrentUser, db: DBSession):
    """获取单个数据源详情"""
    service = DataSourceService(db)
    item = await service.get_data_source(data_source_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="获取数据源成功", data=DataSourceResponse.model_validate(item))


@router.post("", response_model=BaseResponse[DataSourceResponse], status_code=status.HTTP_201_CREATED)
async def create_data_source(data: DataSourceCreate, current_user: CurrentUser, db: DBSession):
    """创建数据源"""
    service = DataSourceService(db)
    item = await service.create_data_source(current_user.id, data)
    return BaseResponse(success=True, code=201, msg="创建数据源成功", data=DataSourceResponse.model_validate(item))


@router.put("/{data_source_id}", response_model=BaseResponse[DataSourceResponse])
async def update_data_source(
    data_source_id: int,
    data: DataSourceUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """更新数据源"""
    service = DataSourceService(db)
    item = await service.update_data_source(data_source_id, current_user.id, data)
    return BaseResponse(success=True, code=200, msg="更新数据源成功", data=DataSourceResponse.model_validate(item))


@router.delete("/{data_source_id}", response_model=BaseResponse[None])
async def delete_data_source(data_source_id: int, current_user: CurrentUser, db: DBSession):
    """删除数据源"""
    service = DataSourceService(db)
    await service.delete_data_source(data_source_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="删除数据源成功", data=None)


@router.post("/{data_source_id}/test", response_model=BaseResponse[DataSourceTestResult])
async def test_data_source_connection(data_source_id: int, current_user: CurrentUser, db: DBSession):
    """测试数据源连接"""
    from app.services.db_connector import DBConnectorService

    # 获取数据源
    service = DataSourceService(db)
    data_source = await service.get_data_source(data_source_id, current_user.id)

    # 测试连接
    connector = DBConnectorService()
    result = await connector.test_connection(data_source)

    return BaseResponse(success=True, code=200, msg="测试完成", data=result)


@router.post("/{data_source_id}/sync-schema", response_model=BaseResponse[DataSourceSchemaResponse])
async def sync_data_source_schema(data_source_id: int, current_user: CurrentUser, db: DBSession):
    """同步数据源 Schema"""
    from app.core.exceptions import BadRequestException
    from app.models.data_source import DataSourceType
    from app.schemas.data_source import ColumnSchema, TableSchema
    from app.services.db_connector import DBConnectorService

    # 获取数据源（包含关联文件）
    service = DataSourceService(db)
    data_source = await service.get_data_source_with_file(data_source_id, current_user.id)

    if data_source.source_type == DataSourceType.DATABASE.value:
        # 数据库类型：使用 DBConnector 提取 schema
        connector = DBConnectorService()
        schema = await connector.extract_schema(data_source)
    elif data_source.source_type == DataSourceType.FILE.value:
        # 文件类型：从关联的 UploadedFile 获取 schema
        if not data_source.uploaded_file:
            raise BadRequestException(msg="文件数据源未关联文件")

        uploaded_file = data_source.uploaded_file
        if uploaded_file.status != "ready":
            raise BadRequestException(msg="文件尚未处理完成")

        # 从 columns_info 构建 ColumnSchema
        columns = []
        for col_info in uploaded_file.columns_info or []:
            columns.append(
                ColumnSchema(
                    name=col_info.get("name", ""),
                    data_type=col_info.get("dtype", col_info.get("type", "unknown")),
                    nullable=col_info.get("nullable", True),
                    primary_key=False,
                )
            )

        # 构建单表 schema（文件作为一个表）
        table = TableSchema(
            name=uploaded_file.original_name,
            columns=columns,
            row_count=uploaded_file.row_count,
        )
        schema = DataSourceSchemaResponse(tables=[table])
    else:
        raise BadRequestException(msg=f"不支持的数据源类型: {data_source.source_type}")

    # 更新缓存
    await service.update_schema_cache(
        data_source_id, current_user.id, {"tables": [t.model_dump() for t in schema.tables]}
    )

    return BaseResponse(success=True, code=200, msg="Schema 同步成功", data=schema)


@router.get("/{data_source_id}/schema", response_model=BaseResponse[DataSourceSchemaResponse])
async def get_data_source_schema(data_source_id: int, current_user: CurrentUser, db: DBSession):
    """获取数据源 Schema（从缓存）"""
    from datetime import datetime

    from app.schemas.data_source import DataSourceSchemaResponse, TableSchema

    service = DataSourceService(db)
    data_source = await service.get_data_source(data_source_id, current_user.id)

    if not data_source.schema_cache:
        return BaseResponse(
            success=True,
            code=200,
            msg="Schema 缓存为空，请先同步",
            data=DataSourceSchemaResponse(tables=[], synced_at=None),
        )

    tables = [TableSchema.model_validate(t) for t in data_source.schema_cache.get("tables", [])]
    synced_at_str = data_source.schema_cache.get("synced_at")
    synced_at = datetime.fromisoformat(synced_at_str) if synced_at_str else None

    return BaseResponse(
        success=True,
        code=200,
        msg="获取 Schema 成功",
        data=DataSourceSchemaResponse(tables=tables, synced_at=synced_at),
    )


