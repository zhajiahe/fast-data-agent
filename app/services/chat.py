"""
对话服务 - 基于 LangGraph 实现 AI 数据分析对话

工具设计：
1. list_local_files: 列出沙盒中的文件（分析过程中生成的中间文件、图表、报告等）
2. quick_analysis: 快速分析数据源，返回数据概览（行数、列数、缺失值、数据类型、统计摘要）
3. execute_sql: 执行 DuckDB SQL 查询
4. execute_python: 在沙盒中执行 Python 代码（用于复杂数据处理）
5. generate_chart: 生成图表，基于 plotly 实现
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

import httpx
from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis_session import AnalysisSession
from app.models.chat_message import ChatMessage
from app.models.data_source import DataSource
from app.repositories.chat_message import ChatMessageRepository
from app.repositories.data_source import DataSourceRepository

# ==================== 上下文和状态定义 ====================


@dataclass
class ChatContext:
    """聊天上下文 - 不可变的运行时配置"""

    user_id: int
    thread_id: int


# ==================== 工具定义 ====================


@tool
async def list_local_files(runtime: ToolRuntime) -> Any:
    """
    列出沙盒中的文件。
    用于查看分析过程中生成的中间文件、图表、报告等。
    """
    runtime.stream_writer("正在获取文件列表...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{settings.SANDBOX_URL}/files",
            params={
                "user_id": ctx.user_id,
                "thread_id": ctx.thread_id,
            },
        )
        return response.json()


@tool
async def quick_analysis(
    data_source_id: int,
    runtime: ToolRuntime,
) -> Any:
    """
    快速分析数据源，返回数据概览。
    包括：行数、列数、缺失值统计、数据类型、统计摘要（均值、中位数、标准差等）。

    Args:
        data_source_id: 数据源 ID，从可用数据源列表中选择
    """
    runtime.stream_writer(f"正在分析数据源 {data_source_id}...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.SANDBOX_URL}/quick_analysis",
            params={
                "user_id": ctx.user_id,
                "thread_id": ctx.thread_id,
                "data_source_id": data_source_id,
            },
        )
        return response.json()


@tool
async def execute_sql(
    sql: str,
    runtime: ToolRuntime,
) -> Any:
    """
    执行 DuckDB SQL 查询。
    支持对已加载的数据源进行 SQL 查询分析。

    Args:
        sql: 要执行的 SQL 查询语句
    """
    runtime.stream_writer("正在执行 SQL 查询...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{settings.SANDBOX_URL}/execute_sql",
            params={
                "user_id": ctx.user_id,
                "thread_id": ctx.thread_id,
            },
            json={"sql": sql},
        )
        return response.json()


@tool
async def execute_python(
    code: str,
    runtime: ToolRuntime,
) -> Any:
    """
    在沙盒中执行 Python 代码，用于复杂数据处理和分析。
    可以使用 pandas、numpy 等数据分析库。

    Args:
        code: 要执行的 Python 代码
    """
    runtime.stream_writer("正在执行 Python 代码...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    async with httpx.AsyncClient(timeout=settings.SANDBOX_TIMEOUT) as client:
        response = await client.post(
            f"{settings.SANDBOX_URL}/execute_python",
            params={
                "user_id": ctx.user_id,
                "thread_id": ctx.thread_id,
            },
            json={"code": code},
        )
        return response.json()


@tool
async def generate_chart(
    chart_type: str,
    data_config: dict,
    title: str,
    runtime: ToolRuntime,
) -> Any:
    """
    生成 Plotly 图表。

    Args:
        chart_type: 图表类型，如 'bar', 'line', 'scatter', 'pie', 'histogram'
        data_config: 图表数据配置，包含 x, y, labels 等
        title: 图表标题
    """
    runtime.stream_writer(f"正在生成 {chart_type} 图表...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.SANDBOX_URL}/generate_chart",
            params={
                "user_id": ctx.user_id,
                "thread_id": ctx.thread_id,
            },
            json={
                "chart_type": chart_type,
                "data_config": data_config,
                "title": title,
            },
        )
        return response.json()


# ==================== 聊天服务 ====================


class ChatService:
    """聊天服务 - 基于 LangGraph ReAct Agent"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.data_source_repo = DataSourceRepository(db)
        self.message_repo = ChatMessageRepository(db)
        self.tools = [
            list_local_files,
            quick_analysis,
            execute_sql,
            execute_python,
            generate_chart,
        ]

    def _get_llm(self, *, temperature: float = 0.0):
        """获取 LLM 实例"""
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
            base_url=settings.OPENAI_API_BASE,
            timeout=60,
            streaming=True,
        )

    def _format_data_sources(self, data_sources: list[DataSource]) -> str:
        """格式化数据源信息供 LLM 使用"""
        if not data_sources:
            return "当前没有可用的数据源。"

        lines = ["可用的数据源列表："]
        for ds in data_sources:
            info = f"- ID: {ds.id}, 名称: {ds.name}, 类型: {ds.source_type}"
            if ds.description:
                info += f", 描述: {ds.description}"
            if ds.schema_cache:
                tables = ds.schema_cache.get("tables", [])
                if tables:
                    table_names = [t.get("name", "") for t in tables[:5]]
                    info += f", 包含表: {', '.join(table_names)}"
                    if len(tables) > 5:
                        info += f" 等共 {len(tables)} 个表"
            lines.append(info)

        return "\n".join(lines)

    def _get_system_prompt(self, data_sources: list[DataSource]) -> str:
        """构建系统提示词"""
        data_source_info = self._format_data_sources(data_sources)

        return f"""你是一个专业的数据分析助手，擅长帮助用户理解和分析数据。

## 你的能力
1. **数据探索**：快速分析数据源，了解数据结构和基本统计信息
2. **SQL 查询**：使用 DuckDB SQL 对数据进行查询和分析
3. **Python 分析**：执行复杂的数据处理和分析代码
4. **可视化**：生成各种图表帮助用户理解数据

## 可用数据源
{data_source_info}

## 工作流程
1. 首先理解用户的分析需求
2. 如果需要，先使用 quick_analysis 了解数据概况
3. 根据需求选择合适的工具进行分析
4. 清晰地解释分析结果，并给出见解和建议

## 注意事项
- 对于 SQL 查询，请确保语法正确，并注意数据量，必要时使用 LIMIT
- 生成图表时，选择最能展示数据特点的图表类型
- 如果分析过程中发现有趣的模式或异常，主动向用户报告
- 保持回复简洁明了，使用中文与用户交流
"""

    def _create_agent(self, data_sources: list[DataSource]):
        """创建 ReAct Agent"""
        return create_agent(
            model=self._get_llm(),
            tools=self.tools,
            system_prompt=self._get_system_prompt(data_sources),
            context_schema=ChatContext,
        )

    async def get_history(
        self,
        session_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[ChatMessage], int]:
        """
        获取会话的历史消息

        Args:
            session_id: 会话 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (消息列表, 总数)
        """
        messages = await self.message_repo.get_by_session(session_id, skip=skip, limit=limit)
        total = await self.message_repo.count_by_session(session_id)
        return messages, total

    async def get_history_as_langchain(
        self,
        session_id: int,
        *,
        limit: int = 50,
    ) -> list[BaseMessage]:
        """
        获取会话历史并转换为 LangChain 消息格式

        Args:
            session_id: 会话 ID
            limit: 最大消息数

        Returns:
            LangChain 消息列表
        """
        messages = await self.message_repo.get_by_session(session_id, limit=limit)
        return self.message_repo.to_langchain_messages(messages)

    async def chat(
        self,
        content: str,
        session: AnalysisSession,
        *,
        stream_mode: str = "messages",
        save_messages: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        发送消息并获取 AI 响应（流式）

        Args:
            content: 用户消息内容
            session: 分析会话
            stream_mode: 流模式 ("values", "updates", "messages", "custom")
            save_messages: 是否保存消息到数据库

        Yields:
            流式状态/消息字典
        """
        # 获取会话关联的数据源
        data_source_ids = session.data_source_ids or []
        data_sources = []
        if data_source_ids:
            data_sources = await self.data_source_repo.get_by_ids(
                data_source_ids, session.user_id
            )

        # 创建 Agent
        agent = self._create_agent(data_sources)

        # 创建上下文
        context = ChatContext(
            user_id=session.user_id,
            thread_id=session.id,
        )

        # 配置
        config = {"context": context}

        # 获取历史消息
        history = await self.get_history_as_langchain(session.id, limit=50)

        # 保存用户消息
        user_message = HumanMessage(content=content)
        if save_messages:
            await self.message_repo.save_langchain_message(
                session.id, user_message, session.user_id
            )

        # 初始状态，包含历史消息
        initial_state = {
            "messages": [*history, user_message],
        }

        # 最后一个 chunk 用于保存消息
        last_chunk: dict[str, Any] | None = None

        try:
            # 流式执行 Agent
            async for chunk in agent.astream(
                initial_state,
                config,
                stream_mode=stream_mode,
            ):
                last_chunk = chunk
                yield chunk

            # 保存 AI 响应消息（只保存新增的消息）
            if save_messages and last_chunk and "messages" in last_chunk:
                final_messages = last_chunk["messages"]
                if isinstance(final_messages, list):
                    # 计算新增的消息（排除历史和用户消息）
                    new_count = len(final_messages) - len(history) - 1
                    if new_count > 0:
                        new_messages = final_messages[-new_count:]
                        await self.message_repo.save_langchain_messages(
                            session.id, new_messages, session.user_id
                        )

        except Exception as e:
            yield {
                "error": {"message": str(e), "type": type(e).__name__},
            }
