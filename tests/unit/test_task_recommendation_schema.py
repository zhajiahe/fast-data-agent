"""
任务推荐 Schema 单元测试

测试 Pydantic 模型的验证逻辑
"""

import pytest
from pydantic import ValidationError

from app.schemas.task_recommendation import (
    GenerateFollowupRequest,
    GenerateRecommendationsRequest,
    TaskRecommendationCreate,
    TaskRecommendationUpdate,
)


class TestTaskRecommendationCreateSchema:
    """任务推荐创建 Schema 测试类"""

    @pytest.mark.unit
    def test_valid_create(self):
        """测试有效的推荐创建数据"""
        data = TaskRecommendationCreate(
            title="测试推荐",
            description="这是一个测试推荐",
            category="overview",
            source_type="initial",
            priority=0,
        )
        assert data.title == "测试推荐"
        assert data.description == "这是一个测试推荐"
        assert data.category == "overview"
        assert data.source_type == "initial"
        assert data.priority == 0

    @pytest.mark.unit
    def test_create_with_defaults(self):
        """测试使用默认值创建"""
        data = TaskRecommendationCreate(
            title="仅标题",
        )
        assert data.title == "仅标题"
        assert data.description is None
        assert data.category == "overview"
        assert data.source_type == "initial"
        assert data.priority == 0

    @pytest.mark.unit
    def test_title_too_long(self):
        """测试标题太长"""
        with pytest.raises(ValidationError) as exc_info:
            TaskRecommendationCreate(
                title="a" * 201,  # 超过 200 字符
            )
        assert "title" in str(exc_info.value)

    @pytest.mark.unit
    def test_negative_priority(self):
        """测试负数优先级"""
        with pytest.raises(ValidationError) as exc_info:
            TaskRecommendationCreate(
                title="测试",
                priority=-1,
            )
        assert "priority" in str(exc_info.value)


class TestTaskRecommendationUpdateSchema:
    """任务推荐更新 Schema 测试类"""

    @pytest.mark.unit
    def test_valid_update(self):
        """测试有效的状态更新"""
        data = TaskRecommendationUpdate(status="selected")
        assert data.status == "selected"

    @pytest.mark.unit
    def test_update_dismissed(self):
        """测试更新为 dismissed"""
        data = TaskRecommendationUpdate(status="dismissed")
        assert data.status == "dismissed"


class TestGenerateRecommendationsRequestSchema:
    """生成推荐请求 Schema 测试类"""

    @pytest.mark.unit
    def test_default_values(self):
        """测试默认值"""
        data = GenerateRecommendationsRequest()
        assert data.max_count == 5
        assert data.force_regenerate is False

    @pytest.mark.unit
    def test_custom_values(self):
        """测试自定义值"""
        data = GenerateRecommendationsRequest(max_count=3, force_regenerate=True)
        assert data.max_count == 3
        assert data.force_regenerate is True

    @pytest.mark.unit
    def test_max_count_too_large(self):
        """测试 max_count 超出范围"""
        with pytest.raises(ValidationError) as exc_info:
            GenerateRecommendationsRequest(max_count=20)
        assert "max_count" in str(exc_info.value)

    @pytest.mark.unit
    def test_max_count_too_small(self):
        """测试 max_count 太小"""
        with pytest.raises(ValidationError) as exc_info:
            GenerateRecommendationsRequest(max_count=0)
        assert "max_count" in str(exc_info.value)


class TestGenerateFollowupRequestSchema:
    """生成追问推荐请求 Schema 测试类"""

    @pytest.mark.unit
    def test_valid_request(self):
        """测试有效的追问请求"""
        data = GenerateFollowupRequest(
            conversation_context="用户询问了销售数据",
            last_result={"total_sales": 10000},
            max_count=3,
        )
        assert data.conversation_context == "用户询问了销售数据"
        assert data.last_result == {"total_sales": 10000}
        assert data.max_count == 3

    @pytest.mark.unit
    def test_minimal_request(self):
        """测试最小请求"""
        data = GenerateFollowupRequest(
            conversation_context="简单上下文",
        )
        assert data.conversation_context == "简单上下文"
        assert data.last_result is None
        assert data.max_count == 3

    @pytest.mark.unit
    def test_missing_context(self):
        """测试缺少 conversation_context"""
        with pytest.raises(ValidationError) as exc_info:
            GenerateFollowupRequest()  # type: ignore[call-arg]
        assert "conversation_context" in str(exc_info.value)

    @pytest.mark.unit
    def test_max_count_boundary(self):
        """测试 max_count 边界值"""
        data = GenerateFollowupRequest(
            conversation_context="测试",
            max_count=5,  # 最大允许值
        )
        assert data.max_count == 5

        with pytest.raises(ValidationError):
            GenerateFollowupRequest(
                conversation_context="测试",
                max_count=6,  # 超出最大值
            )


