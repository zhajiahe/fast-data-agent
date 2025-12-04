"""
任务推荐 Schema

定义任务推荐相关的请求和响应模型
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TaskRecommendationBase(BaseModel):
    """推荐基础字段"""

    title: str = Field(..., max_length=200, description="推荐任务标题")
    description: str | None = Field(None, description="任务描述")
    category: str = Field(default="overview", description="任务分类")


class TaskRecommendationCreate(TaskRecommendationBase):
    """创建推荐"""

    source_type: str = Field(default="initial", description="推荐来源类型")
    priority: int = Field(default=0, ge=0, description="优先级（0最高）")
    trigger_message_id: int | None = Field(None, description="触发消息ID")


class TaskRecommendationUpdate(BaseModel):
    """更新推荐"""

    status: str = Field(..., description="状态：pending/selected/dismissed")


class TaskRecommendationResponse(BaseModel):
    """推荐响应"""

    id: int
    session_id: int
    title: str
    description: str | None
    category: str
    source_type: str
    priority: int
    status: str
    trigger_message_id: int | None
    create_time: datetime
    update_time: datetime

    model_config = {"from_attributes": True}


class GenerateRecommendationsRequest(BaseModel):
    """生成推荐请求"""

    max_count: int = Field(default=5, ge=1, le=10, description="最大推荐数量")
    force_regenerate: bool = Field(default=False, description="是否强制重新生成（会清理现有pending推荐）")


class GenerateFollowupRequest(BaseModel):
    """生成追问推荐请求"""

    conversation_context: str = Field(..., description="对话上下文")
    last_result: dict | None = Field(None, description="上次分析结果")
    max_count: int = Field(default=3, ge=1, le=5, description="最大推荐数量")
    trigger_message_id: int | None = Field(None, description="触发消息ID")
