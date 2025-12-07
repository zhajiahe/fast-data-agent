"""
对话服务 - 基于 LangGraph 实现 AI 数据分析对话

工具设计：
1. list_local_files: 列出沙盒中的文件（分析过程中生成的中间文件、图表、报告等）
2. quick_analysis: 快速分析数据源，返回数据概览（行数、列数、缺失值、数据类型、统计摘要）
3. execute_sql: 执行 DuckDB SQL 查询
4. execute_python: 在沙盒中执行 Python 代码（用于复杂数据处理）
5. generate_chart: 生成图表，基于 plotly 实现
"""

import warnings
from collections.abc import AsyncGenerator
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

# ==================== LLM 实例缓存 ====================


class LLMCache:
    """
    LLM 实例缓存
    - 避免重复创建 LLM 实例的开销（~180ms）
    - 按温度参数缓存不同实例
    """

    _instances: dict[float, ChatOpenAI] = {}

    @classmethod
    def get(cls, temperature: float = 0.0) -> ChatOpenAI:
        """获取或创建 LLM 实例"""
        if temperature not in cls._instances:
            cls._instances[temperature] = ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=temperature,
                api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
                base_url=settings.OPENAI_API_BASE,
                timeout=60,
                streaming=True,
            )
            logger.debug(f"创建 LLM 实例: temperature={temperature}")
        return cls._instances[temperature]

    @classmethod
    def clear(cls) -> None:
        """清空缓存"""
        cls._instances.clear()


from app.models.data_source import DataSource
from app.models.message import ChatMessage
from app.models.session import AnalysisSession
from app.repositories.data_source import DataSourceRepository
from app.repositories.message import ChatMessageRepository
from app.utils.tools import (
    ChatContext,
    DataSourceContext,
    execute_python,
    execute_sql,
    generate_chart,
    get_sandbox_client,
    list_local_files,
    quick_analysis,
)

# 过滤 LangGraph 内部序列化时的 Pydantic 警告
# 这是由于 context_schema 在序列化时与内部状态模式不完全匹配导致的，不影响功能
warnings.filterwarnings(
    "ignore",
    message="Pydantic serializer warnings",
    category=UserWarning,
    module="pydantic.main",
)

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
            generate_chart,
            execute_sql,
            execute_python,
        ]

    def _get_llm(self, *, temperature: float = 0.0):
        """获取 LLM 实例（使用缓存）"""
        return LLMCache.get(temperature)

    def _format_data_sources(self, data_sources: list[DataSource]) -> str:
        """格式化数据源信息供 LLM 使用"""
        if not data_sources:
            return "当前没有可用的数据源。"

        lines = ["可用的数据源："]
        for ds in data_sources:
            # 基础信息
            lines.append(f"- **{ds.name}** (ID: {ds.id})")
            lines.append(f"  - 类型: {ds.source_type}")
            lines.append(f'  - SQL 访问: `SELECT * FROM "{ds.name}" LIMIT 10`')
            if ds.description:
                lines.append(f"  - 描述: {ds.description}")
            if ds.schema_cache:
                tables = ds.schema_cache.get("tables", [])
                if tables:
                    table_names = [t.get("name", "") for t in tables[:5]]
                    info = ", ".join(table_names)
                    if len(tables) > 5:
                        info += f" 等共 {len(tables)} 个表"
                    lines.append(f"  - 包含表: {info}")

        return "\n".join(lines)

    def _format_local_files(self, files: list[dict[str, Any]]) -> str:
        """格式化会话文件列表"""
        if not files:
            return "暂无文件"

        lines = []
        for f in files[:10]:  # 最多显示 10 个文件
            name = f.get("name", "")
            size = f.get("size", 0)
            # 格式化文件大小
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f}KB"
            else:
                size_str = f"{size / 1024 / 1024:.1f}MB"
            lines.append(f"- {name} ({size_str})")

        if len(files) > 10:
            lines.append(f"- ... 等共 {len(files)} 个文件")

        return "\n".join(lines)

    async def _get_local_files(self, user_id: int, session_id: int) -> list[dict[str, Any]]:
        """获取会话本地文件列表"""
        try:
            client = get_sandbox_client()
            response = await client.get(
                "/files",
                params={"user_id": user_id, "thread_id": session_id},
            )
            result = response.json()
            return result.get("files", []) if result.get("success") else []
        except Exception as e:
            logger.warning(f"获取会话文件失败: {e}")
            return []

    async def _get_system_prompt(
        self,
        data_sources: list[DataSource],
        user_id: int,
        session_id: int,
    ) -> str:
        """构建系统提示词"""
        data_source_info = self._format_data_sources(data_sources)

        # 获取会话文件列表
        local_files = await self._get_local_files(user_id, session_id)
        local_files_info = self._format_local_files(local_files)

        return f"""你是专业的数据分析助手，可以分析用户上传的文件或配置的数据源。

## 可用工具
| 工具 | 用途 |
|------|------|
| quick_analysis | 获取数据概况（行数、列数、类型、统计摘要）|
| execute_sql | DuckDB SQL 查询，结果自动保存为 parquet |
| generate_chart | 基于数据生成 Plotly 图表 |
| execute_python | 复杂数据处理和自定义分析 |
| list_local_files | 查看会话中已生成的文件 |

## 数据源
{data_source_info}

## 当前会话文件
{local_files_info}

## 数据访问规则 ⚠️
1. **访问数据源**：在 execute_sql 中使用数据源名称，如 `SELECT * FROM "数据源名称"`
2. **读取 SQL 结果**：execute_sql 返回的 result_file 可用于后续分析，如 `SELECT * FROM 'sql_result_xxx.parquet'`
3. **generate_chart**：先用 execute_sql 查询数据，再用返回的 parquet 文件绘图

## 要点
- SQL 查询大数据量时使用 LIMIT
- 使用中文交流
"""

    async def _create_agent(self, data_sources: list[DataSource], user_id: int, session_id: int):
        """创建 ReAct Agent"""
        system_prompt = await self._get_system_prompt(data_sources, user_id, session_id)
        return create_agent(
            model=self._get_llm(),
            tools=self.tools,
            system_prompt=system_prompt,
            context_schema=ChatContext,
        )

    def _build_data_source_contexts(self, data_sources: list[DataSource]) -> list[DataSourceContext]:
        """将 DataSource 模型转换为 DataSourceContext"""
        contexts = []
        for ds in data_sources:
            # 构建基础参数
            ctx_data: dict[str, Any] = {
                "id": ds.id,
                "name": ds.name,
                "source_type": ds.source_type,
            }

            if ds.source_type == "file" and ds.uploaded_file:
                # 文件类型数据源
                ctx_data["file_type"] = ds.uploaded_file.file_type
                ctx_data["object_key"] = ds.uploaded_file.object_key
                ctx_data["bucket_name"] = ds.uploaded_file.bucket_name
            elif ds.source_type == "database":
                # 数据库类型数据源
                ctx_data["db_type"] = ds.db_type
                ctx_data["host"] = ds.host
                ctx_data["port"] = ds.port
                ctx_data["database"] = ds.database
                ctx_data["username"] = ds.username
                ctx_data["password"] = ds.password

            contexts.append(DataSourceContext(**ctx_data))

        return contexts

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
        save_messages: bool = True,
    ) -> AsyncGenerator[dict[str, Any] | tuple[Any, Any], None]:
        """
        发送消息并获取 AI 响应（流式）

        使用 stream_mode=["values", "messages"] 同时流式传输：
        - "messages": LLM token 流，直接 yield (message, metadata) 用于实时显示
        - "values": 完整状态快照，用于获取最终消息（不 yield，仅内部使用）

        Args:
            content: 用户消息内容
            session: 分析会话
            save_messages: 是否保存消息到数据库

        Yields:
            流式 (message, metadata) 元组，或 error dict
        """
        # 获取会话关联的数据源
        data_source_ids = session.data_source_ids or []
        data_sources: list[DataSource] = []
        if data_source_ids:
            data_sources = await self.data_source_repo.get_by_ids(data_source_ids, session.user_id)

        # 创建 Agent
        agent = await self._create_agent(data_sources, session.user_id, session.id)

        # 构建数据源上下文列表
        ds_contexts = self._build_data_source_contexts(data_sources)

        # 创建上下文
        context = ChatContext(
            user_id=session.user_id,
            thread_id=session.id,
            data_sources=ds_contexts,
        )
        logger.debug(f"上下文: {context}")

        # 获取历史消息
        history = await self.get_history_as_langchain(session.id, limit=50)

        # 保存用户消息
        user_message = HumanMessage(content=content)
        if save_messages:
            await self.message_repo.save_langchain_message(session.id, user_message, session.user_id)

        # 初始状态，包含历史消息
        initial_state = {
            "messages": [*history, user_message],
        }
        logger.debug(f"初始状态: {initial_state}")

        # 记录历史消息数量，用于过滤新消息
        history_count = len(history) + 1  # +1 是用户消息
        final_messages: list[BaseMessage] = []

        try:
            # 使用多模式流式传输：
            # - "messages": LLM token 流
            # - "updates": 状态更新（包含工具调用和结果）
            # - "values": 完整状态快照（用于获取最终消息）
            async for mode, chunk in agent.astream(
                initial_state,
                context=context,
                stream_mode=["values", "updates", "messages"],
            ):
                if mode == "messages":
                    # token 流：直接 yield (message_chunk, metadata) 元组
                    yield chunk

                elif mode == "updates":
                    # 状态更新：包含节点执行结果（工具调用、工具结果等）
                    yield {"mode": "updates", "data": chunk}

                elif mode == "values":
                    # 完整状态快照：提取新产生的消息（用于保存）
                    all_messages = chunk.get("messages", [])
                    final_messages = all_messages[history_count:]

            # 保存响应消息（从完整状态中获取，无需手动聚合 token）
            if save_messages and final_messages:
                # 过滤规则：
                # 1. 排除 HumanMessage（用户消息在发送时已保存）
                # 2. 保留有内容的消息
                # 3. 保留有 tool_calls 的 AIMessage（即使 content 为空）
                messages_to_save = [
                    msg
                    for msg in final_messages
                    if not isinstance(msg, HumanMessage)
                    and (
                        getattr(msg, "content", None)  # 有内容
                        or (isinstance(msg, AIMessage) and msg.tool_calls)  # 或有工具调用
                    )
                ]
                if messages_to_save:
                    logger.debug(f"保存 {len(messages_to_save)} 条消息")
                    await self.message_repo.save_langchain_messages(session.id, messages_to_save, session.user_id)
                    # 显式 commit，确保消息在发送 [DONE] 之前持久化
                    # 避免前端 refetch 时看不到最新消息
                    await self.db.commit()

        except Exception as e:
            yield {
                "error": {"message": str(e), "type": type(e).__name__},
            }
