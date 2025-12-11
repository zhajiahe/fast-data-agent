"""
数据库连接相关的 Pydantic Schema
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.database_connection import DatabaseType


class DatabaseConnectionBase(BaseModel):
    """数据库连接基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="连接名称")
    description: str | None = Field(default=None, description="连接描述")


class DatabaseConnectionConfig(BaseModel):
    """数据库连接配置"""

    db_type: DatabaseType = Field(..., description="数据库类型")
    host: str = Field(..., min_length=1, max_length=255, description="数据库主机")
    port: int = Field(..., ge=1, le=65535, description="数据库端口")
    database: str = Field(..., min_length=1, max_length=100, description="数据库名")
    username: str = Field(..., min_length=1, max_length=100, description="用户名")
    password: str = Field(..., min_length=1, max_length=255, description="密码")
    extra_params: dict[str, Any] | None = Field(default=None, description="额外连接参数")


class DatabaseConnectionCreate(DatabaseConnectionBase):
    """创建数据库连接请求"""

    config: DatabaseConnectionConfig = Field(..., description="连接配置")


class DatabaseConnectionUpdate(BaseModel):
    """更新数据库连接请求"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="连接名称")
    description: str | None = Field(default=None, description="连接描述")
    config: DatabaseConnectionConfig | None = Field(default=None, description="连接配置")


class DatabaseConnectionResponse(DatabaseConnectionBase):
    """数据库连接响应（不返回密码）"""

    id: uuid.UUID = Field(..., description="连接ID")
    user_id: uuid.UUID = Field(..., description="所属用户ID")

    # 连接配置（不返回密码）
    db_type: DatabaseType = Field(..., description="数据库类型")
    host: str = Field(..., description="数据库主机")
    port: int = Field(..., description="数据库端口")
    database: str = Field(..., description="数据库名")
    username: str = Field(..., description="用户名")
    extra_params: dict[str, Any] | None = Field(default=None, description="额外连接参数")

    # 状态
    last_tested_at: str | None = Field(default=None, description="最后测试时间")
    is_active: bool = Field(default=True, description="是否可用")

    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    model_config = {"from_attributes": True}


class AutoCreatedRawData(BaseModel):
    """自动创建的 RawData 简要信息"""

    raw_data_id: uuid.UUID = Field(..., description="数据对象ID")
    name: str = Field(..., description="数据对象名称")
    table_name: str = Field(..., description="来源表名")
    status: str = Field(..., description="状态: created/ready/error")
    error_message: str | None = Field(default=None, description="错误信息（如果有）")


class DatabaseConnectionWithRawResponse(DatabaseConnectionResponse):
    """数据库连接响应（包含自动创建的 RawData 结果）"""

    auto_raw_results: list[AutoCreatedRawData] | None = Field(default=None, description="自动创建 RawData 的结果列表")
    auto_raw_error: str | None = Field(default=None, description="自动创建 RawData 的错误信息")


class DatabaseConnectionTestResult(BaseModel):
    """数据库连接测试结果"""

    success: bool = Field(..., description="是否连接成功")
    message: str = Field(..., description="测试结果消息")
    latency_ms: int | None = Field(default=None, description="连接延迟（毫秒）")


class DatabaseTableInfo(BaseModel):
    """数据库表信息"""

    schema_name: str = Field(..., description="Schema名称")
    table_name: str = Field(..., description="表名")
    table_type: str = Field(default="TABLE", description="表类型: TABLE/VIEW")
    comment: str | None = Field(default=None, description="表注释")


class DatabaseConnectionTablesResponse(BaseModel):
    """数据库连接的表列表响应"""

    connection_id: uuid.UUID = Field(..., description="连接ID")
    tables: list[DatabaseTableInfo] = Field(default_factory=list, description="表列表")


class TableColumnInfo(BaseModel):
    """数据库表的列信息"""

    name: str = Field(..., description="列名")
    data_type: str = Field(..., description="数据类型")
    nullable: bool = Field(default=True, description="是否可空")
    primary_key: bool = Field(default=False, description="是否主键")
    comment: str | None = Field(default=None, description="列注释")


class DatabaseTableSchemaResponse(BaseModel):
    """数据库表结构响应"""

    connection_id: uuid.UUID = Field(..., description="连接ID")
    schema_name: str | None = Field(default=None, description="Schema 名称")
    table_name: str = Field(..., description="表名")
    columns: list[TableColumnInfo] = Field(default_factory=list, description="列信息")
    row_count: int | None = Field(default=None, description="行数估算")
