"""
数据库连接管理 API 路由
"""

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.schemas.database_connection import (
    DatabaseConnectionCreate,
    DatabaseConnectionResponse,
    DatabaseConnectionTablesResponse,
    DatabaseConnectionTestResult,
    DatabaseConnectionUpdate,
    DatabaseTableInfo,
)
from app.services.database_connection import DatabaseConnectionService

router = APIRouter(prefix="/database-connections", tags=["database-connections"])


@router.get("", response_model=BaseResponse[PageResponse[DatabaseConnectionResponse]])
async def get_connections(
    db: DBSession,
    current_user: CurrentUser,
    page_query: BasePageQuery = Depends(),
    keyword: str | None = None,
    db_type: str | None = None,
):
    """获取数据库连接列表（分页）"""
    service = DatabaseConnectionService(db)
    items, total = await service.get_connections(
        user_id=current_user.id,
        keyword=keyword,
        db_type=db_type,
        page_num=page_query.page_num,
        page_size=page_query.page_size,
    )
    data_list = [DatabaseConnectionResponse.model_validate(item) for item in items]
    return BaseResponse(
        success=True,
        code=200,
        msg="获取连接列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=total,
            items=data_list,
        ),
    )


@router.get("/{connection_id}", response_model=BaseResponse[DatabaseConnectionResponse])
async def get_connection(connection_id: int, current_user: CurrentUser, db: DBSession):
    """获取单个数据库连接详情"""
    service = DatabaseConnectionService(db)
    item = await service.get_connection(connection_id, current_user.id)
    return BaseResponse(
        success=True,
        code=200,
        msg="获取连接成功",
        data=DatabaseConnectionResponse.model_validate(item),
    )


@router.post("", response_model=BaseResponse[DatabaseConnectionResponse], status_code=status.HTTP_201_CREATED)
async def create_connection(data: DatabaseConnectionCreate, current_user: CurrentUser, db: DBSession):
    """创建数据库连接"""
    service = DatabaseConnectionService(db)
    item = await service.create_connection(current_user.id, data)
    return BaseResponse(
        success=True,
        code=201,
        msg="创建连接成功",
        data=DatabaseConnectionResponse.model_validate(item),
    )


@router.put("/{connection_id}", response_model=BaseResponse[DatabaseConnectionResponse])
async def update_connection(
    connection_id: int,
    data: DatabaseConnectionUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """更新数据库连接"""
    service = DatabaseConnectionService(db)
    item = await service.update_connection(connection_id, current_user.id, data)
    return BaseResponse(
        success=True,
        code=200,
        msg="更新连接成功",
        data=DatabaseConnectionResponse.model_validate(item),
    )


@router.delete("/{connection_id}", response_model=BaseResponse[None])
async def delete_connection(connection_id: int, current_user: CurrentUser, db: DBSession):
    """删除数据库连接"""
    service = DatabaseConnectionService(db)
    await service.delete_connection(connection_id, current_user.id)
    return BaseResponse(success=True, code=200, msg="删除连接成功", data=None)


@router.post("/{connection_id}/test", response_model=BaseResponse[DatabaseConnectionTestResult])
async def test_connection(connection_id: int, current_user: CurrentUser, db: DBSession):
    """测试数据库连接"""
    from app.services.db_connector import DBConnectorService

    # 获取连接
    service = DatabaseConnectionService(db)
    connection = await service.get_connection(connection_id, current_user.id)

    # 测试连接
    connector = DBConnectorService()
    result = await connector.test_database_connection(connection)

    # 更新测试状态
    await service.update_test_status(connection_id, current_user.id, is_active=result.success)

    return BaseResponse(success=True, code=200, msg="测试完成", data=result)


@router.get("/{connection_id}/tables", response_model=BaseResponse[DatabaseConnectionTablesResponse])
async def get_connection_tables(connection_id: int, current_user: CurrentUser, db: DBSession):
    """获取数据库连接的表列表"""
    from app.services.db_connector import DBConnectorService

    # 获取连接
    service = DatabaseConnectionService(db)
    connection = await service.get_connection(connection_id, current_user.id)

    # 获取表列表
    connector = DBConnectorService()
    tables_info = await connector.get_tables(connection)

    tables = [
        DatabaseTableInfo(
            schema_name=t.get("schema", ""),
            table_name=t.get("name", ""),
            table_type=t.get("type", "TABLE"),
            comment=t.get("comment"),
        )
        for t in tables_info
    ]

    return BaseResponse(
        success=True,
        code=200,
        msg="获取表列表成功",
        data=DatabaseConnectionTablesResponse(connection_id=connection_id, tables=tables),
    )
