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
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis_session import AnalysisSession
from app.models.chat_message import ChatMessage
from app.models.data_source import DataSource
from app.repositories.chat_message import ChatMessageRepository
from app.repositories.data_source import DataSourceRepository
from app.utils.tools import ChatContext, DataSourceContext, list_local_files, quick_analysis

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
        data_sources: list[DataSource] = []
        if data_source_ids:
            data_sources = await self.data_source_repo.get_by_ids(data_source_ids, session.user_id)

        # 创建 Agent
        agent = self._create_agent(data_sources)

        # 构建数据源上下文列表
        ds_contexts = self._build_data_source_contexts(data_sources)

        # 创建上下文
        context = ChatContext(
            user_id=session.user_id,
            thread_id=session.id,
            data_sources=ds_contexts,
        )
        logger.info(f"上下文: {context}")

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
        logger.info(f"初始状态: {initial_state}")
        # 收集流式消息用于保存
        message_contents: dict[str, str] = {}  # 消息内容
        message_types: dict[str, type] = {}  # 消息类型
        message_artifacts: dict[str, Any] = {}  # 工具消息的 artifact

        try:
            # 流式执行 Agent，context 直接作为参数传递
            async for chunk in agent.astream(
                initial_state,
                context=context,
                stream_mode=stream_mode,
            ):
                yield chunk

                # stream_mode="messages" 返回 (message, metadata) tuple
                # 流式模式下收到的是 MessageChunk，需要聚合内容
                if isinstance(chunk, tuple) and len(chunk) >= 2:
                    message, _metadata = chunk
                    # 只保存非用户消息的内容
                    if not isinstance(message, HumanMessage):
                        content = getattr(message, "content", "")
                        msg_id = getattr(message, "id", None)

                        if msg_id:
                            # 记录消息类型（取第一个 chunk 的类型）
                            if msg_id not in message_types:
                                message_types[msg_id] = type(message)
                                message_contents[msg_id] = ""

                            # 聚合内容
                            if content:
                                message_contents[msg_id] += content

                            # 收集 artifact（如果有）
                            artifact = getattr(message, "artifact", None)
                            if artifact and msg_id not in message_artifacts:
                                message_artifacts[msg_id] = artifact

            # 保存响应消息
            if save_messages and message_contents:
                from langchain_core.messages import AIMessage, ToolMessage

                messages_to_save: list[BaseMessage] = []
                for msg_id, content in message_contents.items():
                    if not content.strip():
                        continue

                    msg_type = message_types.get(msg_id)
                    msg_type_name = msg_type.__name__ if msg_type else "Unknown"

                    # 根据消息类型创建对应的消息对象
                    if msg_type and "ToolMessage" in msg_type_name:
                        # ToolMessage 包含 artifact（如果有）
                        artifact = message_artifacts.get(msg_id)
                        messages_to_save.append(ToolMessage(content=content, tool_call_id=msg_id, artifact=artifact))
                    else:
                        # AIMessage 或其他类型
                        messages_to_save.append(AIMessage(content=content, id=msg_id))

                if messages_to_save:
                    logger.debug(f"保存 {len(messages_to_save)} 条消息")
                    await self.message_repo.save_langchain_messages(session.id, messages_to_save, session.user_id)

        except Exception as e:
            yield {
                "error": {"message": str(e), "type": type(e).__name__},
            }
