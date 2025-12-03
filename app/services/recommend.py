"""
任务推荐服务 - 基于数据源 Schema 和对话上下文生成分析任务推荐

核心功能：
1. 初始任务推荐（基于数据源 Schema）
2. 追问推荐（基于对话上下文）
3. 推荐优先级排序
"""

import json
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis_session import AnalysisSession
from app.models.data_source import DataSource
from app.models.task_recommendation import RecommendationCategory, RecommendationSourceType


# ==================== 数据模型 ====================


class RecommendationItem(BaseModel):
    """推荐项"""

    title: str = Field(..., description="推荐任务标题")
    description: str = Field(..., description="任务描述")
    category: str = Field(default="other", description="分类")
    priority: int | None = Field(default=None, ge=0, description="优先级，0最高")
    source_type: str = Field(default="initial", description="推荐来源类型")
    task_payload: dict = Field(default_factory=dict, description="任务参数")


class RecommendationResult(BaseModel):
    """推荐结果"""

    recommendations: list[RecommendationItem] = Field(default_factory=list)


# ==================== 推荐服务 ====================


class RecommendService:
    """任务推荐服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _resolve_model_identifier(self) -> str:
        """获取 LangChain init_chat_model 所需的模型 ID"""
        model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        if ":" in model_name:
            return model_name
        return f"openai:{model_name}"

    def _get_llm(self, *, temperature: float | None = None):
        """获取 LLM 实例（参考最新 LangChain init_chat_model API）"""
        temp = 0.3 if temperature is None else temperature
        return init_chat_model(
            self._resolve_model_identifier(),
            temperature=temp,
            timeout=45,
        )

    def _get_structured_llm(self, schema: type[BaseModel], *, temperature: float | None = None):
        """返回带结构化输出能力的模型"""
        return self._get_llm(temperature=temperature).with_structured_output(schema)

    async def _request_structured_recommendations(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
    ) -> RecommendationResult:
        """调用带结构化输出的模型"""
        structured_llm = self._get_structured_llm(RecommendationResult, temperature=temperature)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        return await structured_llm.ainvoke(messages)

    def _normalize_recommendations(
        self,
        items: list[RecommendationItem],
        source_type: RecommendationSourceType,
        max_count: int,
    ) -> list[RecommendationItem]:
        """规范化 LLM 输出，确保字段完整"""
        normalized: list[RecommendationItem] = []
        for idx, item in enumerate(items[:max_count]):
            normalized.append(
                RecommendationItem(
                    title=item.title,
                    description=item.description,
                    category=item.category or RecommendationCategory.OTHER.value,
                    priority=item.priority if item.priority is not None else idx,
                    source_type=source_type.value,
                    task_payload=item.task_payload or {},
                )
            )
        return normalized

    async def generate_initial_recommendations(
        self,
        session: AnalysisSession,
        data_sources: list[DataSource],
        max_count: int = 5,
    ) -> list[RecommendationItem]:
        """
        生成初始任务推荐

        基于数据源的 Schema 信息，生成适合该数据集的分析任务推荐

        Args:
            session: 分析会话
            data_sources: 数据源列表
            max_count: 最大推荐数量

        Returns:
            推荐任务列表
        """
        # 收集 Schema 信息
        schema_info = self._collect_schema_info(data_sources)

        if not schema_info:
            # 如果没有 Schema 信息，返回通用推荐
            return self._get_generic_recommendations()

        # 使用 LLM 生成推荐
        try:
            recommendations = await self._generate_with_llm(
                schema_info=schema_info,
                source_type=RecommendationSourceType.INITIAL,
                max_count=max_count,
            )
            if recommendations:
                return recommendations
        except (ValidationError, Exception):
            pass

        # LLM 调用失败时返回基于规则的推荐
        return self._generate_rule_based_recommendations(schema_info, max_count)

    async def generate_followup_recommendations(
        self,
        session: AnalysisSession,
        data_sources: list[DataSource],
        conversation_context: str,
        last_result: dict | None = None,
        max_count: int = 3,
    ) -> list[RecommendationItem]:
        """
        生成追问推荐

        基于对话上下文和上一次分析结果，生成追问建议

        Args:
            session: 分析会话
            data_sources: 数据源列表
            conversation_context: 对话上下文
            last_result: 上一次分析结果
            max_count: 最大推荐数量

        Returns:
            推荐任务列表
        """
        schema_info = self._collect_schema_info(data_sources)

        try:
            recommendations = await self._generate_followup_with_llm(
                schema_info=schema_info,
                conversation_context=conversation_context,
                last_result=last_result,
                max_count=max_count,
            )
            if recommendations:
                return recommendations
        except (ValidationError, Exception):
            pass

        return self._get_generic_followup_recommendations()

    def _collect_schema_info(self, data_sources: list[DataSource]) -> dict[str, Any]:
        """收集数据源 Schema 信息"""
        schema_info = {}
        for ds in data_sources:
            if ds.schema_cache:
                schema_info[ds.name] = {
                    "type": ds.source_type,
                    "db_type": ds.db_type,
                    "tables": ds.schema_cache.get("tables", []),
                }
        return schema_info

    async def _generate_with_llm(
        self,
        schema_info: dict,
        source_type: RecommendationSourceType,
        max_count: int,
    ) -> list[RecommendationItem]:
        """使用 LLM 生成推荐"""
        system_prompt = """你是一个资深数据分析顾问。请严格按照 RecommendationResult 模型填充 recommendations 字段，
并确保每个推荐都能帮助用户快速理解或深入分析数据。"""

        user_prompt = f"""数据库 Schema 信息：
{json.dumps(schema_info, ensure_ascii=False, indent=2)}

请基于以上数据结构生成不超过 {max_count} 个高价值分析任务。"""

        result = await self._request_structured_recommendations(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )
        return self._normalize_recommendations(result.recommendations, source_type, max_count)

    async def _generate_followup_with_llm(
        self,
        schema_info: dict,
        conversation_context: str,
        last_result: dict | None,
        max_count: int,
    ) -> list[RecommendationItem]:
        """使用 LLM 生成追问推荐"""
        system_prompt = """你是一个资深数据分析顾问。请在 RecommendationResult 模型中补充 recommendations，
用于引导用户基于当前上下文提出更深入的问题或分析任务。"""

        context_parts = [f"对话上下文：\n{conversation_context}"]
        if last_result:
            context_parts.append(f"上次分析结果：\n{json.dumps(last_result, ensure_ascii=False, indent=2)}")
        if schema_info:
            context_parts.append(f"可用数据：\n{json.dumps(schema_info, ensure_ascii=False, indent=2)}")

        user_prompt = "\n\n".join(context_parts) + f"\n\n请生成不超过 {max_count} 个追问建议。"

        result = await self._request_structured_recommendations(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
        )
        return self._normalize_recommendations(
            result.recommendations,
            RecommendationSourceType.FOLLOW_UP,
            max_count,
        )

    def _generate_rule_based_recommendations(
        self,
        schema_info: dict,
        max_count: int,
    ) -> list[RecommendationItem]:
        """基于规则生成推荐"""
        recommendations = []

        # 分析 Schema 中的表和列
        all_tables = []
        has_time_column = False
        has_numeric_column = False
        has_category_column = False

        for ds_name, ds_info in schema_info.items():
            for table in ds_info.get("tables", []):
                all_tables.append(table.get("name", "unknown"))
                for col in table.get("columns", []):
                    col_type = col.get("data_type", "").lower()
                    col_name = col.get("name", "").lower()

                    if any(t in col_type for t in ["timestamp", "date", "time"]):
                        has_time_column = True
                    if any(t in col_type for t in ["int", "float", "decimal", "numeric"]):
                        has_numeric_column = True
                    if any(t in col_type for t in ["varchar", "text", "char"]):
                        if any(k in col_name for k in ["type", "category", "status", "level"]):
                            has_category_column = True

        # 基于发现生成推荐
        priority = 0

        # 总是添加概览
        recommendations.append(
            RecommendationItem(
                title="查看数据概览",
                description=f"分析 {len(all_tables)} 个数据表的基本信息和统计",
                category=RecommendationCategory.OVERVIEW.value,
                priority=priority,
                source_type=RecommendationSourceType.INITIAL.value,
            )
        )
        priority += 1

        if has_time_column:
            recommendations.append(
                RecommendationItem(
                    title="分析时间趋势",
                    description="查看数据随时间的变化规律",
                    category=RecommendationCategory.TREND.value,
                    priority=priority,
                    source_type=RecommendationSourceType.INITIAL.value,
                )
            )
            priority += 1

        if has_category_column:
            recommendations.append(
                RecommendationItem(
                    title="分类对比分析",
                    description="对比不同类别的数据差异",
                    category=RecommendationCategory.COMPARISON.value,
                    priority=priority,
                    source_type=RecommendationSourceType.INITIAL.value,
                )
            )
            priority += 1

        if has_numeric_column:
            recommendations.append(
                RecommendationItem(
                    title="数值分布分析",
                    description="分析数值字段的分布情况",
                    category=RecommendationCategory.DISTRIBUTION.value,
                    priority=priority,
                    source_type=RecommendationSourceType.INITIAL.value,
                )
            )
            priority += 1

            recommendations.append(
                RecommendationItem(
                    title="异常值检测",
                    description="识别数据中的异常值和离群点",
                    category=RecommendationCategory.ANOMALY.value,
                    priority=priority,
                    source_type=RecommendationSourceType.INITIAL.value,
                )
            )
            priority += 1

        return recommendations[:max_count]

    def _get_generic_recommendations(self) -> list[RecommendationItem]:
        """获取通用推荐（当无法分析 Schema 时）"""
        return [
            RecommendationItem(
                title="查看数据概览",
                description="了解数据集的基本信息和结构",
                category=RecommendationCategory.OVERVIEW.value,
                priority=0,
                source_type=RecommendationSourceType.INITIAL.value,
            ),
            RecommendationItem(
                title="数据质量检查",
                description="检查数据完整性和质量问题",
                category=RecommendationCategory.OTHER.value,
                priority=1,
                source_type=RecommendationSourceType.INITIAL.value,
            ),
            RecommendationItem(
                title="基础统计分析",
                description="计算各字段的基础统计指标",
                category=RecommendationCategory.DISTRIBUTION.value,
                priority=2,
                source_type=RecommendationSourceType.INITIAL.value,
            ),
        ]

    def _get_generic_followup_recommendations(self) -> list[RecommendationItem]:
        """获取通用追问推荐"""
        return [
            RecommendationItem(
                title="深入分析细节",
                description="对当前结果进行更详细的分析",
                category=RecommendationCategory.OTHER.value,
                priority=0,
                source_type=RecommendationSourceType.FOLLOW_UP.value,
            ),
            RecommendationItem(
                title="对比其他维度",
                description="从其他角度分析数据",
                category=RecommendationCategory.COMPARISON.value,
                priority=1,
                source_type=RecommendationSourceType.FOLLOW_UP.value,
            ),
            RecommendationItem(
                title="导出分析报告",
                description="生成当前分析的汇总报告",
                category=RecommendationCategory.OTHER.value,
                priority=2,
                source_type=RecommendationSourceType.FOLLOW_UP.value,
            ),
        ]

