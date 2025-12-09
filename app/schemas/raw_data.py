"""
原始数据相关的 Pydantic Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.models.raw_data import RawDataType


class ColumnSchema(BaseModel):
    """列结构"""

    name: str = Field(..., description="列名")
    data_type: str = Field(..., description="数据类型")
    nullable: bool = Field(default=True, description="是否可空")
    user_type_override: str | None = Field(default=None, description="用户修正的类型")
    comment: str | None = Field(default=None, description="列注释")


class RawDataBase(BaseModel):
    """原始数据基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="原始数据名称")
    description: str | None = Field(default=None, description="原始数据描述")
    raw_type: RawDataType = Field(..., description="原始数据类型: database_table/file")


class RawDataDatabaseTableConfig(BaseModel):
    """数据库表类型配置"""

    connection_id: int = Field(..., description="数据库连接ID")
    schema_name: str | None = Field(default=None, max_length=100, description="Schema名称")
    table_name: str | None = Field(default=None, max_length=100, description="表名")
    custom_sql: str | None = Field(default=None, description="自定义SQL查询（可选）")

    @model_validator(mode="after")
    def validate_table_or_sql(self) -> "RawDataDatabaseTableConfig":
        """验证：必须提供 table_name 或 custom_sql"""
        if not self.table_name and not self.custom_sql:
            raise ValueError("必须提供 table_name 或 custom_sql")
        return self


class RawDataFileConfig(BaseModel):
    """文件类型配置"""

    file_id: int = Field(..., description="上传文件ID")


class RawDataCreate(RawDataBase):
    """创建原始数据请求"""

    # 数据库表类型配置
    database_table_config: RawDataDatabaseTableConfig | None = Field(
        default=None, description="数据库表配置（raw_type=database_table 时必填）"
    )
    # 文件类型配置
    file_config: RawDataFileConfig | None = Field(default=None, description="文件配置（raw_type=file 时必填）")

    @model_validator(mode="after")
    def validate_config(self) -> "RawDataCreate":
        """验证配置与类型匹配"""
        if self.raw_type == RawDataType.DATABASE_TABLE:
            if not self.database_table_config:
                raise ValueError("数据库表类型必须提供 database_table_config")
        elif self.raw_type == RawDataType.FILE:
            if not self.file_config:
                raise ValueError("文件类型必须提供 file_config")
        return self


class RawDataUpdate(BaseModel):
    """更新原始数据请求"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="原始数据名称")
    description: str | None = Field(default=None, description="原始数据描述")
    # 数据库表类型配置
    database_table_config: RawDataDatabaseTableConfig | None = Field(default=None, description="数据库表配置")
    # 文件类型配置
    file_config: RawDataFileConfig | None = Field(default=None, description="文件配置")


class RawDataColumnUpdate(BaseModel):
    """更新列类型请求"""

    columns: list[ColumnSchema] = Field(..., description="列结构列表（支持修正类型）")


class RawDataResponse(RawDataBase):
    """原始数据响应"""

    id: int = Field(..., description="原始数据ID")
    user_id: int = Field(..., description="所属用户ID")

    # 数据库表配置
    connection_id: int | None = Field(default=None, description="数据库连接ID")
    schema_name: str | None = Field(default=None, description="Schema名称")
    table_name: str | None = Field(default=None, description="表名")
    custom_sql: str | None = Field(default=None, description="自定义SQL")

    # 文件配置
    file_id: int | None = Field(default=None, description="上传文件ID")

    # 元数据
    columns_schema: list[ColumnSchema] | None = Field(default=None, description="列结构信息")
    row_count_estimate: int | None = Field(default=None, description="估算行数")
    synced_at: str | None = Field(default=None, description="最后同步时间")

    # 状态
    status: str = Field(default="pending", description="状态: pending/syncing/ready/error")
    error_message: str | None = Field(default=None, description="错误信息")

    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    model_config = {"from_attributes": True}


class RawDataListQuery(BaseModel):
    """原始数据列表查询参数"""

    keyword: str | None = Field(default=None, description="搜索关键词")
    raw_type: RawDataType | None = Field(default=None, description="原始数据类型")
    status: str | None = Field(default=None, description="状态过滤")


class RawDataPreviewRequest(BaseModel):
    """原始数据预览请求"""

    limit: int = Field(default=100, ge=1, le=1000, description="预览行数")


class RawDataPreviewResponse(BaseModel):
    """原始数据预览响应"""

    columns: list[ColumnSchema] = Field(default_factory=list, description="列结构")
    rows: list[dict[str, Any]] = Field(default_factory=list, description="数据行")
    total_rows: int | None = Field(default=None, description="总行数（估算）")
    preview_at: str = Field(..., description="预览时间")


# ==================== 批量创建 ====================


class TableSelection(BaseModel):
    """表选择"""

    schema_name: str | None = Field(default=None, description="Schema 名称")
    table_name: str = Field(..., min_length=1, max_length=255, description="表名")
    custom_name: str | None = Field(default=None, description="自定义显示名称（可选）")


class BatchCreateFromConnectionRequest(BaseModel):
    """从数据库连接批量创建原始数据请求"""

    connection_id: int = Field(..., description="数据库连接ID")
    tables: list[TableSelection] = Field(..., min_length=1, description="要创建的表列表")
    auto_sync: bool = Field(default=True, description="是否自动同步列信息")
    name_prefix: str | None = Field(default=None, description="名称前缀（可选）")


class BatchCreateResult(BaseModel):
    """批量创建结果"""

    raw_data_id: int = Field(..., description="创建的原始数据ID")
    name: str = Field(..., description="原始数据名称")
    table_name: str = Field(..., description="表名")
    status: str = Field(..., description="状态: created/syncing/ready/error")
    error_message: str | None = Field(default=None, description="错误信息（如果有）")


class BatchCreateFromConnectionResponse(BaseModel):
    """从数据库连接批量创建原始数据响应"""

    success_count: int = Field(..., description="成功创建的数量")
    failed_count: int = Field(..., description="失败的数量")
    results: list[BatchCreateResult] = Field(default_factory=list, description="每个表的创建结果")
