"""
数据源相关的 Pydantic Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.data_source import DataSourceCategory


class TargetField(BaseModel):
    """目标字段定义"""

    name: str = Field(..., min_length=1, max_length=100, description="字段名")
    data_type: str = Field(..., description="数据类型")
    description: str | None = Field(default=None, description="字段描述")


class FieldMapping(BaseModel):
    """单个 Raw 的字段映射"""

    raw_data_id: int = Field(..., description="原始数据ID")
    mappings: dict[str, str | None] = Field(..., description="字段映射: {target_field: source_field_or_null}")
    priority: int = Field(default=0, description="优先级（数值越大优先级越高）")
    is_enabled: bool = Field(default=True, description="是否启用")


class DataSourceBase(BaseModel):
    """数据源基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="数据源名称")
    description: str | None = Field(default=None, description="数据源描述")
    category: DataSourceCategory | None = Field(default=None, description="数据源分类")


class DataSourceCreate(DataSourceBase):
    """创建数据源请求"""

    # 目标字段定义
    target_fields: list[TargetField] = Field(default_factory=list, description="目标字段定义")
    # Raw 数据映射
    raw_mappings: list[FieldMapping] = Field(default_factory=list, description="原始数据字段映射")


class DataSourceUpdate(BaseModel):
    """更新数据源请求"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="数据源名称")
    description: str | None = Field(default=None, description="数据源描述")
    category: DataSourceCategory | None = Field(default=None, description="数据源分类")

    # 更新目标字段
    target_fields: list[TargetField] | None = Field(default=None, description="目标字段定义")
    # 更新 Raw 映射
    raw_mappings: list[FieldMapping] | None = Field(default=None, description="原始数据字段映射")


class RawMappingResponse(BaseModel):
    """Raw 映射响应"""

    id: int = Field(..., description="映射ID")
    raw_data_id: int = Field(..., description="原始数据ID")
    raw_data_name: str | None = Field(default=None, description="原始数据名称")
    field_mappings: dict[str, str | None] = Field(default_factory=dict, description="字段映射")
    priority: int = Field(default=0, description="优先级")
    is_enabled: bool = Field(default=True, description="是否启用")


class DataSourceResponse(DataSourceBase):
    """数据源响应"""

    id: int = Field(..., description="数据源ID")
    user_id: int = Field(..., description="所属用户ID")

    # 目标字段
    target_fields: list[TargetField] | None = Field(default=None, description="目标字段定义")

    # Schema 缓存
    schema_cache: dict[str, Any] | None = Field(default=None, description="表结构缓存")

    # Raw 映射
    raw_mappings: list[RawMappingResponse] | None = Field(default=None, description="原始数据映射")

    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    model_config = {"from_attributes": True}


class DataSourceListQuery(BaseModel):
    """数据源列表查询参数"""

    keyword: str | None = Field(default=None, description="搜索关键词")
    category: DataSourceCategory | None = Field(default=None, description="数据源分类")


class DataSourcePreviewRequest(BaseModel):
    """数据源预览请求（合并后的数据）"""

    limit: int = Field(default=100, ge=1, le=1000, description="预览行数")


class DataSourcePreviewResponse(BaseModel):
    """数据源预览响应"""

    columns: list[TargetField] = Field(default_factory=list, description="字段定义")
    rows: list[dict[str, Any]] = Field(default_factory=list, description="合并后的数据行")
    source_stats: dict[str, int] = Field(default_factory=dict, description="各 Raw 源的行数统计")
    preview_at: str = Field(..., description="预览时间")
