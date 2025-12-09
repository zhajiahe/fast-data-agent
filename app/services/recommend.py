"""
任务推荐服务 - 基于数据源 Schema 和对话上下文生成分析任务推荐

核心功能：
1. 初始任务推荐（基于数据源 Schema）
2. 追问推荐（基于对话上下文）
3. 推荐优先级排序
4. 推荐持久化（保存到数据库）
"""

import json
from typing import Any

from langchain.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.data_source import DataSource
from app.models.recommendation import (
    RecommendationCategory,
    RecommendationSourceType,
    TaskRecommendation,
)
from app.models.session import AnalysisSession
from app.repositories.recommendation import TaskRecommendationRepository

# ==================== 数据模型 ====================


class RecommendationItem(BaseModel):
    """推荐项"""

    title: str = Field(..., description="推荐任务标题")
    description: str = Field(..., description="任务描述")
    category: str = Field(default="other", description="分类")
    priority: int | None = Field(default=None, ge=0, description="优先级，0最高")
    source_type: str = Field(default="initial", description="推荐来源类型")


class RecommendationResult(BaseModel):
    """推荐结果"""

    recommendations: list[RecommendationItem] = Field(default_factory=list)


# ==================== 推荐服务 ====================


class RecommendService:
    """任务推荐服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TaskRecommendationRepository(db)

    def _get_llm(self, *, temperature: float | None = None):
        """获取 LLM 实例（参考最新 LangChain init_chat_model API）"""
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0 if temperature is None else temperature,
            api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
            base_url=settings.OPENAI_API_BASE,
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
        result = await structured_llm.ainvoke(messages)
        if isinstance(result, RecommendationResult):
            return result
        # 如果模型返回的不是预期类型，返回空结果
        return RecommendationResult()

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
                )
            )
        return normalized

    def _format_session_context(self, session: AnalysisSession) -> str:
        """构建会话上下文描述，辅助 LLM 生成更贴合的推荐"""
        description = session.description or "未提供"
        config_summary = json.dumps(session.config or {}, ensure_ascii=False, indent=2)
        return (
            f"会话ID: {session.id}\n"
            f"会话名称: {session.name}\n"
            f"会话描述: {description}\n"
            f"历史消息数: {session.message_count}\n"
            f"额外配置: {config_summary}"
        )

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
        logger.debug(f"收集到 {len(schema_info)} 个数据源的 Schema 信息")

        if not schema_info:
            # 如果没有 Schema 信息，尝试使用数据源名称生成推荐
            logger.warning("数据源没有 Schema 缓存，使用数据源名称生成推荐")
            return self._get_recommendations_without_schema(data_sources)

        # 使用 LLM 生成推荐
        try:
            recommendations = await self._generate_with_llm(
                session=session,
                schema_info=schema_info,
                source_type=RecommendationSourceType.INITIAL,
                max_count=max_count,
            )
            if recommendations:
                return recommendations
            logger.warning("LLM 返回空推荐列表，使用规则生成")
        except ValidationError as e:
            logger.warning(f"LLM 推荐结果验证失败: {e}")
        except Exception as e:
            logger.warning(f"LLM 生成推荐异常: {e}")

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
                session=session,
                schema_info=schema_info,
                conversation_context=conversation_context,
                last_result=last_result,
                max_count=max_count,
            )
            if recommendations:
                logger.debug(f"LLM 生成了 {len(recommendations)} 条追问推荐")
                return recommendations
            logger.warning("LLM 返回空追问推荐列表")
        except ValidationError as e:
            logger.warning(f"LLM 追问推荐结果验证失败: {e}")
        except Exception as e:
            logger.warning(f"LLM 生成追问推荐异常: {e}")

        return self._get_generic_followup_recommendations()

    def _collect_schema_info(self, data_sources: list[DataSource]) -> dict[str, Any]:
        """收集数据源 Schema 信息"""
        schema_info = {}
        for ds in data_sources:
            if ds.schema_cache:
                schema_info[ds.name] = {
                    "category": ds.category,
                    "target_fields": ds.target_fields,
                    "tables": ds.schema_cache.get("tables", []),
                }
        return schema_info

    async def _generate_with_llm(
        self,
        session: AnalysisSession,
        schema_info: dict,
        source_type: RecommendationSourceType,
        max_count: int,
    ) -> list[RecommendationItem]:
        """使用 LLM 生成推荐"""
        session_context = self._format_session_context(session)

        system_prompt = """你是一个资深数据分析顾问。请严格按照 RecommendationResult 模型填充 recommendations 字段，
并确保每个推荐都能帮助用户快速理解或深入分析数据。"""

        user_prompt = f"""当前分析会话：
{session_context}

数据库 Schema 信息：
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
        session: AnalysisSession,
        schema_info: dict,
        conversation_context: str,
        last_result: dict | None,
        max_count: int,
    ) -> list[RecommendationItem]:
        """使用 LLM 生成追问推荐"""
        session_context = self._format_session_context(session)

        system_prompt = """你是一个资深数据分析顾问。请在 RecommendationResult 模型中补充 recommendations，
用于引导用户基于当前上下文提出更深入的问题或分析任务。"""

        context_parts = [
            f"会话信息：\n{session_context}",
            f"对话上下文：\n{conversation_context}",
        ]
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

        for _ds_name, ds_info in schema_info.items():
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

    def _get_recommendations_without_schema(self, data_sources: list[DataSource]) -> list[RecommendationItem]:
        """当数据源没有 Schema 时，基于数据源信息生成推荐"""
        recommendations = []
        priority = 0

        # 获取数据源名称列表
        ds_names = [ds.name for ds in data_sources]
        ds_names_str = "、".join(ds_names) if ds_names else "数据"

        recommendations.append(
            RecommendationItem(
                title=f"快速分析 {ds_names_str}",
                description="获取数据的基本结构、行数、列信息和统计摘要",
                category=RecommendationCategory.OVERVIEW.value,
                priority=priority,
                source_type=RecommendationSourceType.INITIAL.value,
            )
        )
        priority += 1

        # 添加通用推荐
        recommendations.append(
            RecommendationItem(
                title="查看数据预览",
                description="预览数据内容，了解数据格式和字段类型",
                category=RecommendationCategory.OVERVIEW.value,
                priority=priority,
                source_type=RecommendationSourceType.INITIAL.value,
            )
        )
        priority += 1

        recommendations.append(
            RecommendationItem(
                title="数据质量检查",
                description="检查数据完整性、缺失值和异常情况",
                category=RecommendationCategory.ANOMALY.value,
                priority=priority,
                source_type=RecommendationSourceType.INITIAL.value,
            )
        )
        priority += 1

        recommendations.append(
            RecommendationItem(
                title="数值统计分析",
                description="计算数值字段的均值、中位数、标准差等统计指标",
                category=RecommendationCategory.DISTRIBUTION.value,
                priority=priority,
                source_type=RecommendationSourceType.INITIAL.value,
            )
        )

        return recommendations[:5]

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

    # ==================== 持久化方法 ====================

    async def generate_and_save_initial(
        self,
        session: AnalysisSession,
        data_sources: list[DataSource],
        user_id: int,
        max_count: int = 5,
        *,
        force_regenerate: bool = False,
    ) -> list[TaskRecommendation]:
        """
        生成并保存初始推荐

        Args:
            session: 分析会话
            data_sources: 数据源列表
            user_id: 用户 ID
            max_count: 最大推荐数量
            force_regenerate: 是否强制重新生成

        Returns:
            保存的推荐列表
        """
        # 如果强制重新生成，先清理现有推荐
        if force_regenerate:
            await self.repo.delete_by_session(session.id, source_type=RecommendationSourceType.INITIAL.value)

        # 生成推荐
        try:
            items = await self.generate_initial_recommendations(
                session=session,
                data_sources=data_sources,
                max_count=max_count,
            )
        except Exception as e:
            logger.warning(f"生成初始推荐失败: {e}")
            items = self._get_generic_recommendations()

        # 保存到数据库
        return await self.repo.create_from_items(
            session_id=session.id,
            items=[item.model_dump() for item in items],
            user_id=user_id,
        )

    async def generate_and_save_followup(
        self,
        session: AnalysisSession,
        data_sources: list[DataSource],
        conversation_context: str,
        user_id: int,
        *,
        last_result: dict | None = None,
        max_count: int = 3,
        trigger_message_id: int | None = None,
    ) -> list[TaskRecommendation]:
        """
        生成并保存追问推荐

        Args:
            session: 分析会话
            data_sources: 数据源列表
            conversation_context: 对话上下文
            user_id: 用户 ID
            last_result: 上次分析结果
            max_count: 最大推荐数量
            trigger_message_id: 触发消息 ID

        Returns:
            保存的推荐列表
        """
        # 生成推荐
        try:
            items = await self.generate_followup_recommendations(
                session=session,
                data_sources=data_sources,
                conversation_context=conversation_context,
                last_result=last_result,
                max_count=max_count,
            )
        except Exception as e:
            logger.warning(f"生成追问推荐失败: {e}")
            items = self._get_generic_followup_recommendations()

        # 保存到数据库
        return await self.repo.create_from_items(
            session_id=session.id,
            items=[item.model_dump() for item in items],
            user_id=user_id,
            trigger_message_id=trigger_message_id,
        )

    async def get_session_recommendations(
        self,
        session_id: int,
        *,
        status: str | None = None,
        source_type: str | None = None,
    ) -> list[TaskRecommendation]:
        """获取会话的推荐列表"""
        return await self.repo.get_by_session(session_id, status=status, source_type=source_type)

    async def update_recommendation_status(
        self,
        recommendation_id: int,
        status: str,
    ) -> TaskRecommendation | None:
        """更新推荐状态"""
        from app.models.recommendation import RecommendationStatus

        try:
            status_enum = RecommendationStatus(status)
            return await self.repo.update_status(recommendation_id, status_enum)
        except ValueError:
            return None
