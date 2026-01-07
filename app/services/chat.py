"""
对话服务 - 基于 LangGraph 实现 AI 数据分析对话

工具设计：
1. list_local_files: 列出沙盒中的文件（分析过程中生成的中间文件、图表、报告等）
2. quick_analysis: 快速分析数据源，返回数据概览（行数、列数、缺失值、数据类型、统计摘要）
3. execute_sql: 执行 DuckDB SQL 查询
4. execute_python: 在沙盒中执行 Python 代码（用于复杂数据处理）
5. generate_chart: 生成图表，基于 plotly 实现
"""

import uuid
import warnings
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt_str
from app.models.message import ChatMessage
from app.models.raw_data import RawData
from app.models.session import AnalysisSession
from app.repositories.message import ChatMessageRepository
from app.repositories.session import AnalysisSessionRepository
from app.utils.tools import (
    ChatContext,
    RawDataContext,
    execute_python,
    execute_sql,
    generate_chart,
    get_sandbox_client,
    list_local_files,
    quick_analysis,
)

# 会话工厂类型：返回可以作为异步上下文管理器使用的 AsyncSession
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

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
    """聊天服务 - 基于 LangGraph ReAct Agent

    支持两种模式：
    1. 普通模式：传入 db 会话，使用共享会话（适用于短请求）
    2. 流式模式：传入 db_factory 会话工厂，每个数据库操作使用独立会话（适用于流式响应）
    """

    def __init__(
        self,
        db: AsyncSession | None = None,
        *,
        db_factory: SessionFactory | None = None,
    ):
        """
        初始化聊天服务

        Args:
            db: 数据库会话（传统模式，会话在外部管理）
            db_factory: 会话工厂函数（流式模式，每次操作使用新会话）

        Note:
            如果同时提供 db 和 db_factory，优先使用 db_factory（流式模式）
        """
        self._db = db
        self._db_factory = db_factory
        self.tools = [
            list_local_files,
            quick_analysis,
            generate_chart,
            execute_sql,
            execute_python,
        ]

    def _get_shared_db(self) -> AsyncSession:
        """获取共享数据库会话（仅用于传统模式）

        此方法仅在未配置 db_factory 时调用，返回构造时传入的共享会话
        """
        if self._db is not None:
            return self._db
        raise RuntimeError("ChatService 未配置数据库会话")

    def _get_llm(self, *, temperature: float = 0.0):
        """获取 LLM 实例（每次新建，避免全局共享状态）"""
        logger.debug(f"创建 LLM 实例: temperature={temperature}, streaming={settings.LLM_STREAMING}")
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
            base_url=settings.OPENAI_API_BASE,
            timeout=60,
            streaming=settings.LLM_STREAMING,  # 可通过 LLM_STREAMING 环境变量控制
        )

    def _format_raw_data_list(self, raw_data_list: list[RawData]) -> str:
        """格式化数据对象列表供 LLM 使用"""
        if not raw_data_list:
            return "当前没有可用的数据。"

        lines = ["**可用数据：**"]

        for raw in raw_data_list:
            lines.append(f'\n### VIEW: `"{raw.name}"`')

            if raw.description:
                lines.append(f"- 描述: {raw.description}")

            if raw.raw_type == "database_table":
                db_type = raw.connection.db_type if raw.connection else "unknown"
                lines.append(f"- 类型: 数据库表 ({db_type})")
                if raw.table_name:
                    schema = raw.schema_name or "public"
                    lines.append(f"- 源表: {schema}.{raw.table_name}")
            elif raw.raw_type == "file":
                file_type = raw.uploaded_file.file_type if raw.uploaded_file else "unknown"
                lines.append(f"- 类型: 文件 ({file_type})")

            # 列信息
            if raw.columns_schema:
                col_info = ", ".join(f"{c.get('name')}({c.get('data_type', '?')})" for c in raw.columns_schema[:6])
                if len(raw.columns_schema) > 6:
                    col_info += f" ...共{len(raw.columns_schema)}列"
                lines.append(f"- 列: {col_info}")

        return "\n".join(lines)

    def _format_local_files(self, files: list[dict[str, Any]]) -> str:
        """格式化会话文件列表（过滤内部文件）"""
        # 过滤掉内部文件（如 session.duckdb）
        internal_files = {"session.duckdb"}
        user_files = [f for f in files if f.get("name", "") not in internal_files]

        if not user_files:
            return "暂无文件（SQL 查询结果会自动保存为 .parquet 文件）"

        lines = []
        for f in user_files[:10]:  # 最多显示 10 个文件
            name = f.get("name", "")
            size = f.get("size", 0)
            # 格式化文件大小
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f}KB"
            else:
                size_str = f"{size / 1024 / 1024:.1f}MB"
            lines.append(f"- `{name}` ({size_str})")

        if len(user_files) > 10:
            lines.append(f"- ... 等共 {len(user_files)} 个文件")

        return "\n".join(lines)

    async def _get_local_files(self, user_id: Any, session_id: Any) -> list[dict[str, Any]]:
        """获取会话本地文件列表"""
        try:
            client = get_sandbox_client()
            response = await client.get(
                "/files",
                params={"user_id": str(user_id), "thread_id": str(session_id)},
            )
            result = response.json()
            return result.get("files", []) if result.get("success") else []
        except Exception as e:
            logger.warning(f"获取会话文件失败: {e}")
            return []

    async def _get_system_prompt(
        self,
        raw_data_list: list[RawData],
        user_id: Any,
        session_id: Any,
    ) -> str:
        """构建系统提示词"""
        data_info = self._format_raw_data_list(raw_data_list)

        # 获取会话文件列表
        local_files = await self._get_local_files(user_id, session_id)
        local_files_info = self._format_local_files(local_files)

        view_names = [f'"{raw.name}"' for raw in raw_data_list]

        return f"""你是专业的数据分析助手，可以分析用户的数据。

## 可用工具
| 工具 | 用途 |
|------|------|
| quick_analysis | 获取数据概况；可指定 file_name 分析会话文件 |
| execute_sql | DuckDB SQL 查询，结果自动保存为 parquet |
| generate_chart | 基于数据生成 Plotly 图表 |
| execute_python | 复杂数据处理和自定义分析 |
| list_local_files | 查看会话中已生成的文件 |

## 数据
{data_info}

## 可用 VIEW（SQL 表名）
{", ".join(view_names) if view_names else "暂无"}

## 当前会话文件
{local_files_info}

## 数据访问规则 ⚠️
1. **访问数据**：使用 VIEW 名称，如 `SELECT * FROM "view_name"`
2. **读取 SQL 结果**：execute_sql 返回的 result_file 可用于后续分析
3. **分析文件**：quick_analysis(file_name='xxx.parquet') 可分析会话中的文件
4. **generate_chart**：先用 execute_sql 查询数据，再用返回的 parquet 文件绘图

## 要点
- VIEW 名称需用双引号包裹
- SQL 查询大数据量时使用 LIMIT
- 使用中文交流
"""

    async def _create_agent(self, raw_data_list: list[RawData], user_id: Any, session_id: Any):
        """创建 ReAct Agent"""
        system_prompt = await self._get_system_prompt(raw_data_list, user_id, session_id)
        return create_agent(
            model=self._get_llm(),
            tools=self.tools,
            system_prompt=system_prompt,
            context_schema=ChatContext,
        )

    def _build_raw_data_context(self, raw_data_list: list[RawData]) -> list[RawDataContext]:
        """构建 RawData 上下文列表"""
        contexts: list[RawDataContext] = []

        for raw in raw_data_list:
            ctx_data: dict[str, Any] = {
                "id": str(raw.id),
                "name": raw.name,
                "raw_type": raw.raw_type,
            }

            if raw.raw_type == "file" and raw.uploaded_file:
                ctx_data.update(
                    {
                        "file_type": raw.uploaded_file.file_type,
                        "object_key": raw.uploaded_file.object_key,
                        "bucket_name": raw.uploaded_file.bucket_name,
                    }
                )
            elif raw.raw_type == "database_table" and raw.connection:
                ctx_data.update(
                    {
                        "connection_id": str(raw.connection_id) if raw.connection_id else None,
                        "db_type": raw.connection.db_type,
                        "host": raw.connection.host,
                        "port": raw.connection.port,
                        "database": raw.connection.database,
                        "username": raw.connection.username,
                        "password": decrypt_str(raw.connection.password, allow_plaintext=True),
                        "schema_name": raw.schema_name,
                        "table_name": raw.table_name,
                    }
                )

            contexts.append(RawDataContext(**ctx_data))

        return contexts

    async def get_history(
        self,
        session_id: uuid.UUID,
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
        if self._db_factory is not None:
            # 流式模式：使用短生命周期会话
            async with self._db_factory() as db:
                repo = ChatMessageRepository(db)
                messages = await repo.get_by_session(session_id, skip=skip, limit=limit)
                total = await repo.count_by_session(session_id)
                await db.commit()
                return messages, total
        else:
            # 传统模式：使用共享会话
            db = self._get_shared_db()
            repo = ChatMessageRepository(db)
            messages = await repo.get_by_session(session_id, skip=skip, limit=limit)
            total = await repo.count_by_session(session_id)
            return messages, total

    async def get_history_as_langchain(
        self,
        session_id: uuid.UUID,
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
        if self._db_factory is not None:
            # 流式模式：使用短生命周期会话
            async with self._db_factory() as db:
                repo = ChatMessageRepository(db)
                messages = await repo.get_by_session(session_id, limit=limit)
                await db.commit()
                return repo.to_langchain_messages(messages)
        else:
            # 传统模式：使用共享会话
            db = self._get_shared_db()
            repo = ChatMessageRepository(db)
            messages = await repo.get_by_session(session_id, limit=limit)
            return repo.to_langchain_messages(messages)

    async def _save_user_message(
        self,
        session_id: uuid.UUID,
        user_message: HumanMessage,
        user_id: uuid.UUID,
    ) -> None:
        """保存用户消息（使用独立的短事务）"""
        if self._db_factory is not None:
            async with self._db_factory() as db:
                repo = ChatMessageRepository(db)
                await repo.save_langchain_message(session_id, user_message, user_id)
                await db.commit()
        else:
            db = self._get_shared_db()
            repo = ChatMessageRepository(db)
            await repo.save_langchain_message(session_id, user_message, user_id)

    async def _save_response_messages(
        self,
        session_id: uuid.UUID,
        messages_to_save: list[BaseMessage],
        user_id: uuid.UUID,
    ) -> None:
        """保存 AI 响应消息并更新会话计数（使用独立的短事务）"""
        if self._db_factory is not None:
            async with self._db_factory() as db:
                message_repo = ChatMessageRepository(db)
                session_repo = AnalysisSessionRepository(db)

                logger.debug(f"保存 {len(messages_to_save)} 条消息")
                await message_repo.save_langchain_messages(session_id, messages_to_save, user_id)

                # 更新会话消息计数
                try:
                    msg_count = await message_repo.count_by_session(session_id)
                    session_obj = await session_repo.get_by_id(session_id)
                    if session_obj:
                        await session_repo.update(session_obj, {"message_count": msg_count})
                except Exception as update_err:
                    logger.warning(f"更新会话消息计数失败: {update_err}")

                await db.commit()
        else:
            db = self._get_shared_db()
            message_repo = ChatMessageRepository(db)
            session_repo = AnalysisSessionRepository(db)

            logger.debug(f"保存 {len(messages_to_save)} 条消息")
            await message_repo.save_langchain_messages(session_id, messages_to_save, user_id)

            try:
                msg_count = await message_repo.count_by_session(session_id)
                session_obj = await session_repo.get_by_id(session_id)
                if session_obj:
                    await session_repo.update(session_obj, {"message_count": msg_count})
            except Exception as update_err:
                logger.warning(f"更新会话消息计数失败: {update_err}")

    async def chat(
        self,
        content: str,
        session: AnalysisSession,
        raw_data_list: list[RawData] | None = None,
        *,
        save_messages: bool = True,
    ) -> AsyncGenerator[dict[str, Any] | tuple[Any, Any], None]:
        """
        发送消息并获取 AI 响应（流式）

        使用 stream_mode=["values", "messages"] 同时流式传输：
        - "messages": LLM token 流，直接 yield (message, metadata) 用于实时显示
        - "values": 完整状态快照，用于获取最终消息（不 yield，仅内部使用）

        数据库事务策略：
        - 每个数据库操作使用独立的短生命周期事务
        - 避免在流式处理期间长时间占用数据库连接

        Args:
            content: 用户消息内容
            session: 分析会话
            raw_data_list: 已加载的数据对象列表（可选，如果不提供则自动加载）
            save_messages: 是否保存消息到数据库

        Yields:
            流式 (message, metadata) 元组，或 error dict
        """
        # 使用传入的 raw_data_list，如果没有则保持为空
        if raw_data_list is None:
            raw_data_list = []

        # 创建 Agent（无需数据库）
        agent = await self._create_agent(raw_data_list, session.user_id, session.id)

        # 构建上下文（无需数据库）
        raw_data_contexts = self._build_raw_data_context(raw_data_list)
        context = ChatContext(
            user_id=str(session.user_id),
            thread_id=str(session.id),
            raw_data_list=raw_data_contexts,
        )
        logger.debug(f"上下文: {context}")

        # 获取历史消息（使用短事务）
        history = await self.get_history_as_langchain(session.id, limit=50)

        # 保存用户消息（使用短事务）
        user_message = HumanMessage(content=content)
        if save_messages:
            await self._save_user_message(session.id, user_message, session.user_id)

        # 初始状态，包含历史消息
        initial_state = {
            "messages": [*history, user_message],
        }
        logger.debug(f"初始状态: {initial_state}")

        # 记录历史消息数量，用于过滤新消息
        history_count = len(history) + 1  # +1 是用户消息
        final_messages: list[BaseMessage] = []

        try:
            # Agent 流式处理：无数据库连接，只处理 LLM 交互
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

            # 保存响应消息（使用短事务，在流结束后执行）
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
                    await self._save_response_messages(session.id, messages_to_save, session.user_id)

        except Exception as e:
            logger.exception("聊天流处理失败: {}", e)
            error_message = str(e)
            error_type = e.__class__.__name__
            yield {
                "error": {"message": error_message, "type": error_type},
            }
