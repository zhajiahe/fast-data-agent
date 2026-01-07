"""
分析会话相关的 Pydantic Schema
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RawDataBrief(BaseModel):
    """RawData 简要信息"""

    id: uuid.UUID
    name: str
    raw_type: str
    alias: str | None = None

    model_config = {"from_attributes": True}


class AnalysisSessionBase(BaseModel):
    """分析会话基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="会话名称")
    description: str | None = Field(default=None, description="会话描述")


class AnalysisSessionCreate(AnalysisSessionBase):
    """创建分析会话请求"""

    config: dict[str, Any] | None = Field(default=None, description="会话配置")

    # 关联的数据对象
    raw_data_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="关联的数据对象ID列表",
    )

    @model_validator(mode="after")
    def validate_raw_data(self) -> "AnalysisSessionCreate":
        """验证至少指定一个数据对象"""
        if not self.raw_data_ids:
            raise ValueError("至少需要指定一个数据对象")
        return self


class AnalysisSessionUpdate(BaseModel):
    """更新分析会话请求"""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="会话名称")
    description: str | None = Field(default=None, description="会话描述")
    config: dict[str, Any] | None = Field(default=None, description="会话配置")

    # 更新关联的数据对象（可选）
    raw_data_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="更新关联的数据对象ID列表",
    )


class AnalysisSessionResponse(AnalysisSessionBase):
    """分析会话响应"""

    id: uuid.UUID = Field(..., description="会话ID")
    user_id: uuid.UUID = Field(..., description="所属用户ID")
    config: dict[str, Any] | None = Field(default=None, description="会话配置")
    status: str = Field(..., description="会话状态")
    message_count: int = Field(default=0, description="消息数量")

    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    # 关联的数据对象
    raw_data_list: list[RawDataBrief] = Field(
        default_factory=list,
        description="关联的数据对象",
    )

    model_config = {"from_attributes": True}


class AnalysisSessionListQuery(BaseModel):
    """分析会话列表查询参数"""

    keyword: str | None = Field(default=None, description="搜索关键词")
    status: str | None = Field(default=None, description="会话状态")


class AnalysisSessionDetail(AnalysisSessionResponse):
    """分析会话详情（包含完整 RawData 信息）"""

    # 可以扩展更详细的 RawData 信息
    pass
