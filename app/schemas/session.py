"""
分析会话相关的 Pydantic Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field


class AnalysisSessionBase(BaseModel):
    """分析会话基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="会话名称")
    description: str | None = Field(default=None, description="会话描述")


class AnalysisSessionCreate(AnalysisSessionBase):
    """创建分析会话请求"""

    data_source_id: int | None = Field(default=None, description="关联的数据源ID（可选，仅支持单个数据源）")
    config: dict[str, Any] | None = Field(default=None, description="会话配置")


class AnalysisSessionUpdate(BaseModel):
    """更新分析会话请求"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="会话名称")
    description: str | None = Field(default=None, description="会话描述")
    data_source_id: int | None = Field(default=None, description="关联的数据源ID（可选，仅支持单个数据源）")
    config: dict[str, Any] | None = Field(default=None, description="会话配置")


class AnalysisSessionResponse(AnalysisSessionBase):
    """分析会话响应"""

    id: int = Field(..., description="会话ID")
    user_id: int = Field(..., description="所属用户ID")
    data_source_ids: list[int] | None = Field(default=None, description="关联的数据源ID列表（内部存储）")
    config: dict[str, Any] | None = Field(default=None, description="会话配置")
    status: str = Field(..., description="会话状态")
    message_count: int = Field(default=0, description="消息数量")

    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def data_source_id(self) -> int | None:
        """从 data_source_ids 列表中提取第一个 ID"""
        if self.data_source_ids and len(self.data_source_ids) > 0:
            return self.data_source_ids[0]
        return None


class AnalysisSessionListQuery(BaseModel):
    """分析会话列表查询参数"""

    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="会话状态")


class AnalysisSessionDetail(AnalysisSessionResponse):
    """分析会话详情（包含数据源信息）"""

    data_source: "DataSourceResponse | None" = Field(default=None, description="关联的数据源")


# 避免循环导入
from app.schemas.data_source import DataSourceResponse  # noqa: E402

AnalysisSessionDetail.model_rebuild()
