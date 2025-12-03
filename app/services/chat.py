"""
对话服务 - 基于 LangGraph 实现 AI 数据分析对话

核心功能：
1. 流式对话处理
2. SQL 生成与执行
3. 代码生成与执行
4. 工具调用管理
"""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated, Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis_session import AnalysisSession
from app.models.data_source import DataSource


# ==================== 状态定义 ====================


class AgentState(BaseModel):
    """Agent 状态"""

    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    session_id: int = 0
    user_id: int = 0
    data_sources: list[dict] = Field(default_factory=list)
    schema_info: dict = Field(default_factory=dict)
    current_tool_calls: list[dict] = Field(default_factory=list)
    sql_results: list[dict] = Field(default_factory=list)
    recommendations: list[dict] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


# ==================== 工具定义 ====================


@tool
def execute_sql(query: str, data_source_id: int) -> dict:
    """
    执行 SQL 查询

    Args:
        query: SQL 查询语句
        data_source_id: 数据源 ID

    Returns:
        查询结果，包含 columns 和 data
    """
    # 这里是 mock 实现，实际应调用 db_connector
    return {
        "success": True,
        "columns": ["id", "name", "value"],
        "data": [
            {"id": 1, "name": "示例1", "value": 100},
            {"id": 2, "name": "示例2", "value": 200},
        ],
        "row_count": 2,
        "execution_time_ms": 50,
    }


@tool
def execute_python(code: str) -> dict:
    """
    执行 Python 代码进行数据分析

    Args:
        code: Python 代码字符串

    Returns:
        执行结果
    """
    # 这里是 mock 实现，实际应使用沙箱执行
    return {
        "success": True,
        "output": "代码执行成功",
        "result": {"mean": 150, "std": 50},
    }


@tool
def get_table_schema(table_name: str, data_source_id: int) -> dict:
    """
    获取表结构信息

    Args:
        table_name: 表名
        data_source_id: 数据源 ID

    Returns:
        表结构信息
    """
    # Mock 实现
    return {
        "table_name": table_name,
        "columns": [
            {"name": "id", "type": "INTEGER", "nullable": False, "primary_key": True},
            {"name": "name", "type": "VARCHAR(100)", "nullable": True, "primary_key": False},
            {"name": "created_at", "type": "TIMESTAMP", "nullable": True, "primary_key": False},
        ],
        "row_count": 1000,
    }


# ==================== 聊天服务 ====================


class ChatService:
    """聊天服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tools = [execute_sql, execute_python, get_table_schema]
        self.tools_by_name = {t.name: t for t in self.tools}

    def _resolve_model_identifier(self) -> str:
        """获取 LangChain init_chat_model 所需的模型 ID"""
        model_name = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        if ":" in model_name:
            return model_name
        # 参考最新 LangChain 文档，优先使用 provider:MODEL 形式
        return f"openai:{model_name}"

    def _get_llm(self):
        """获取 LLM 实例（基于最新 init_chat_model 接口）"""
        model_identifier = self._resolve_model_identifier()
        return init_chat_model(
            model_identifier,
            temperature=0,
            timeout=60,
        )

    def _build_system_prompt(self, state: AgentState) -> str:
        """构建系统提示"""
        schema_info = json.dumps(state.schema_info, ensure_ascii=False, indent=2) if state.schema_info else "无"

        return f"""你是一个专业的数据分析助手。你可以帮助用户分析数据、执行SQL查询、生成图表等。

## 可用数据源
{json.dumps(state.data_sources, ensure_ascii=False, indent=2) if state.data_sources else "无"}

## 数据库 Schema 信息
{schema_info}

## 工具使用规则
1. 使用 execute_sql 工具执行 SQL 查询
2. 使用 execute_python 工具执行 Python 代码进行复杂分析
3. 使用 get_table_schema 工具获取表结构

## 响应规则
1. 始终用中文回复
2. 对于数据分析结果，提供清晰的解读
3. 在执行查询前，先确认用户意图
4. 如果需要更多信息，主动询问用户
"""

    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        llm = self._get_llm()
        llm_with_tools = llm.bind_tools(self.tools)

        def call_model(state: AgentState) -> dict:
            """调用模型"""
            messages = state.messages
            if not any(isinstance(m, SystemMessage) for m in messages):
                system_prompt = self._build_system_prompt(state)
                messages = [SystemMessage(content=system_prompt)] + list(messages)

            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}

        def should_continue(state: AgentState) -> str:
            """判断是否继续"""
            last_message = state.messages[-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                return "tools"
            return END

        # 构建图
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(self.tools))

        # 设置入口
        workflow.set_entry_point("agent")

        # 添加边
        workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    async def chat_stream(
        self,
        session: AnalysisSession,
        data_sources: list[DataSource],
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话

        Args:
            session: 分析会话
            data_sources: 数据源列表
            user_message: 用户消息

        Yields:
            SSE 格式的事件流
        """
        message_id = str(uuid.uuid4())[:8]

        # 发送开始事件
        yield f"data: {json.dumps({'event': 'start', 'data': {'message_id': message_id}})}\n\n"

        try:
            # 构建初始状态
            state = AgentState(
                messages=[HumanMessage(content=user_message)],
                session_id=session.id,
                user_id=session.user_id,
                data_sources=[
                    {
                        "id": ds.id,
                        "name": ds.name,
                        "type": ds.source_type,
                        "db_type": ds.db_type,
                    }
                    for ds in data_sources
                ],
                schema_info=self._merge_schemas(data_sources),
            )

            # 执行 graph
            graph = self._build_graph()

            async for event in graph.astream_events(state, version="v2"):
                event_type = event.get("event")

                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'event': 'content', 'data': {'content': chunk.content}})}\n\n"

                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = event.get("data", {}).get("input", {})
                    yield f"data: {json.dumps({'event': 'tool_call', 'data': {'tool_name': tool_name, 'tool_args': tool_input}})}\n\n"

                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = event.get("data", {}).get("output", "")
                    yield f"data: {json.dumps({'event': 'tool_result', 'data': {'tool_name': tool_name, 'result': str(tool_output)}})}\n\n"

            # 发送结束事件
            yield f"data: {json.dumps({'event': 'end', 'data': {'timestamp': datetime.now().isoformat()}})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(e)}})}\n\n"

    def _merge_schemas(self, data_sources: list[DataSource]) -> dict:
        """合并多个数据源的 Schema"""
        merged = {}
        for ds in data_sources:
            if ds.schema_cache:
                merged[ds.name] = ds.schema_cache
        return merged

    async def get_context_for_recommendation(
        self,
        session: AnalysisSession,
        data_sources: list[DataSource],
    ) -> dict[str, Any]:
        """
        获取用于推荐的上下文信息

        Args:
            session: 分析会话
            data_sources: 数据源列表

        Returns:
            上下文信息
        """
        return {
            "session_id": session.id,
            "session_name": session.name,
            "data_sources": [
                {
                    "id": ds.id,
                    "name": ds.name,
                    "type": ds.source_type,
                    "schema": ds.schema_cache,
                }
                for ds in data_sources
            ],
            "message_count": session.message_count,
        }

