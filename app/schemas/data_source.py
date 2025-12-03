"""
数据源相关的 Pydantic Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.data_source import DatabaseType, DataSourceType


class DataSourceBase(BaseModel):
    """数据源基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="数据源名称")
    description: str | None = Field(default=None, description="数据源描述")
    source_type: DataSourceType = Field(default=DataSourceType.DATABASE, description="数据源类型")


class DatabaseConnectionConfig(BaseModel):
    """数据库连接配置"""

    db_type: DatabaseType = Field(..., description="数据库类型")
    host: str = Field(..., min_length=1, max_length=255, description="数据库主机")
    port: int = Field(..., ge=1, le=65535, description="数据库端口")
    database: str = Field(..., min_length=1, max_length=100, description="数据库名")
    username: str = Field(..., min_length=1, max_length=100, description="用户名")
    password: str = Field(..., min_length=1, max_length=255, description="密码")
    extra_params: dict[str, Any] | None = Field(default=None, description="额外连接参数")


class DataSourceCreate(DataSourceBase):
    """创建数据源请求"""

    # 数据库连接配置（source_type=database 时必填）
    db_config: DatabaseConnectionConfig | None = Field(default=None, description="数据库连接配置")

    # 文件数据源配置（source_type=file 时必填）
    file_id: int | None = Field(default=None, description="关联的上传文件ID")


class DataSourceUpdate(BaseModel):
    """更新数据源请求"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="数据源名称")
    description: str | None = Field(default=None, description="数据源描述")

    # 数据库连接配置
    db_config: DatabaseConnectionConfig | None = Field(default=None, description="数据库连接配置")


class DataSourceResponse(DataSourceBase):
    """数据源响应"""

    id: int = Field(..., description="数据源ID")
    user_id: int = Field(..., description="所属用户ID")

    # 数据库配置（不返回密码）
    db_type: DatabaseType | None = Field(default=None, description="数据库类型")
    host: str | None = Field(default=None, description="数据库主机")
    port: int | None = Field(default=None, description="数据库端口")
    database: str | None = Field(default=None, description="数据库名")
    username: str | None = Field(default=None, description="用户名")

    # 文件配置
    file_id: int | None = Field(default=None, description="关联的上传文件ID")

    # Schema 缓存
    schema_cache: dict[str, Any] | None = Field(default=None, description="表结构缓存")

    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    model_config = {"from_attributes": True}


class DataSourceListQuery(BaseModel):
    """数据源列表查询参数"""

    keyword: str | None = Field(default=None, description="搜索关键词")
    source_type: DataSourceType | None = Field(default=None, description="数据源类型")


class DataSourceTestResult(BaseModel):
    """数据源连接测试结果"""

    success: bool = Field(..., description="是否连接成功")
    message: str = Field(..., description="测试结果消息")
    latency_ms: int | None = Field(default=None, description="连接延迟（毫秒）")


class TableSchema(BaseModel):
    """表结构"""

    name: str = Field(..., description="表名")
    columns: list["ColumnSchema"] = Field(default_factory=list, description="列信息")
    row_count: int | None = Field(default=None, description="行数（估算）")
    comment: str | None = Field(default=None, description="表注释")


class ColumnSchema(BaseModel):
    """列结构"""

    name: str = Field(..., description="列名")
    data_type: str = Field(..., description="数据类型")
    nullable: bool = Field(default=True, description="是否可空")
    primary_key: bool = Field(default=False, description="是否主键")
    comment: str | None = Field(default=None, description="列注释")


class DataSourceSchemaResponse(BaseModel):
    """数据源 Schema 响应"""

    tables: list[TableSchema] = Field(default_factory=list, description="表列表")
    synced_at: datetime | None = Field(default=None, description="同步时间")
