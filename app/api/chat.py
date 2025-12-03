"""
对话 API 路由（Mock 实现）

提供对话消息和任务推荐的接口
"""

import asyncio
import json
import random
from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse
from app.models.chat_message import MessageRole, MessageType
from app.schemas.chat_message import (
    ChatMessageCreate,
    ChatMessageResponse,
    TaskRecommendationResponse,
)
from app.services.analysis_session import AnalysisSessionService

router = APIRouter(prefix="/sessions/{session_id}", tags=["chat"])


# ==================== Mock 数据生成 ====================


def _generate_mock_sql_response(question: str) -> dict:
    """生成 mock SQL 响应"""
    return {
        "sql_query": "SELECT * FROM users WHERE created_at > '2024-01-01' LIMIT 10;",
        "sql_result": {
            "columns": ["id", "name", "email", "created_at"],
            "data": [
                {"id": 1, "name": "张三", "email": "zhangsan@example.com", "created_at": "2024-01-15"},
                {"id": 2, "name": "李四", "email": "lisi@example.com", "created_at": "2024-02-20"},
                {"id": 3, "name": "王五", "email": "wangwu@example.com", "created_at": "2024-03-10"},
            ],
            "row_count": 3,
        },
        "execution_time_ms": random.randint(50, 200),
    }


def _generate_mock_recommendations() -> list[dict]:
    """生成 mock 任务推荐"""
    recommendations = [
        {
            "title": "查看数据整体分布",
            "description": "分析数据集中各字段的分布情况，识别异常值",
            "category": "overview",
        },
        {
            "title": "分析时间趋势",
            "description": "查看关键指标随时间的变化趋势",
            "category": "trend",
        },
        {
            "title": "对比不同维度",
            "description": "按照不同维度对数据进行分组对比分析",
            "category": "comparison",
        },
    ]
    return random.sample(recommendations, min(3, len(recommendations)))


async def _mock_streaming_response(question: str, session_id: int) -> AsyncGenerator[str, None]:
    """生成 mock 流式响应"""

    # 1. 发送开始事件
    yield f"data: {json.dumps({'event': 'start', 'data': {'message_id': random.randint(1000, 9999)}})}\n\n"
    await asyncio.sleep(0.1)

    # 2. 模拟思考过程
    thinking_text = f"让我分析一下您的问题：「{question}」\n\n"
    for char in thinking_text:
        yield f"data: {json.dumps({'event': 'content', 'data': {'content': char}})}\n\n"
        await asyncio.sleep(0.02)

    # 3. 模拟工具调用
    yield f"data: {json.dumps({'event': 'tool_call', 'data': {'tool_name': 'execute_sql', 'tool_call_id': 'call_001'}})}\n\n"
    await asyncio.sleep(0.5)

    # 4. 模拟工具结果
    sql_result = _generate_mock_sql_response(question)
    yield f"data: {json.dumps({'event': 'tool_result', 'data': {'tool_call_id': 'call_001', 'result': sql_result}})}\n\n"
    await asyncio.sleep(0.2)

    # 5. 生成分析文本
    analysis_text = """
根据查询结果，我发现：

1. **数据量**：共有 3 条符合条件的记录
2. **时间分布**：数据主要集中在 2024 年第一季度
3. **建议**：可以进一步分析用户增长趋势

您还想了解什么？
"""
    for char in analysis_text:
        yield f"data: {json.dumps({'event': 'content', 'data': {'content': char}})}\n\n"
        await asyncio.sleep(0.01)

    # 6. 发送推荐
    recommendations = _generate_mock_recommendations()
    yield f"data: {json.dumps({'event': 'recommendations', 'data': {'items': recommendations}})}\n\n"

    # 7. 发送结束事件
    yield f"data: {json.dumps({'event': 'end', 'data': {'prompt_tokens': random.randint(100, 500), 'completion_tokens': random.randint(200, 800)}})}\n\n"


# ==================== API 端点 ====================


@router.post("/chat", response_class=StreamingResponse)
async def chat(
    session_id: int,
    data: ChatMessageCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    发送消息并获取 AI 响应（SSE 流式）

    返回 Server-Sent Events 格式的流式响应：
    - `start`: 开始生成，包含 message_id
    - `content`: 文本内容片段
    - `tool_call`: 工具调用开始
    - `tool_result`: 工具调用结果
    - `recommendations`: 推荐的后续问题
    - `end`: 生成结束，包含 token 统计
    - `error`: 错误信息
    """
    # 验证会话权限
    service = AnalysisSessionService(db)
    await service.get_session(session_id, current_user.id)

    return StreamingResponse(
        _mock_streaming_response(data.content, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/messages", response_model=BaseResponse[PageResponse[ChatMessageResponse]])
async def get_messages(
    session_id: int,
    current_user: CurrentUser,
    db: DBSession,
    page_query: BasePageQuery = Depends(),
):
    """获取会话的历史消息（分页）"""
    # 验证会话权限
    service = AnalysisSessionService(db)
    await service.get_session(session_id, current_user.id)

    # Mock 数据
    mock_messages = [
        ChatMessageResponse(
            id=1,
            session_id=session_id,
            role=MessageRole.USER,
            message_type=MessageType.TEXT,
            content="帮我分析一下用户数据",
            create_time=datetime.now(),
        ),
        ChatMessageResponse(
            id=2,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.TEXT,
            content="好的，我来帮您分析用户数据。根据查询结果，发现...",
            sql_query="SELECT * FROM users LIMIT 10",
            sql_result={"columns": ["id", "name"], "data": [{"id": 1, "name": "测试"}]},
            execution_time_ms=120,
            prompt_tokens=150,
            completion_tokens=300,
            create_time=datetime.now(),
        ),
    ]

    return BaseResponse(
        success=True,
        code=200,
        msg="获取消息列表成功",
        data=PageResponse(
            page_num=page_query.page_num,
            page_size=page_query.page_size,
            total=len(mock_messages),
            items=mock_messages,
        ),
    )


@router.get("/recommendations", response_model=BaseResponse[list[TaskRecommendationResponse]])
async def get_recommendations(
    session_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """获取任务推荐列表"""
    # 验证会话权限
    service = AnalysisSessionService(db)
    await service.get_session(session_id, current_user.id)

    # Mock 数据
    mock_recommendations = [
        TaskRecommendationResponse(
            id=1,
            session_id=session_id,
            title="分析用户增长趋势",
            description="查看用户注册数量随时间的变化趋势",
            category="trend",
            status="pending",
            create_time=datetime.now(),
        ),
        TaskRecommendationResponse(
            id=2,
            session_id=session_id,
            title="用户地区分布",
            description="分析用户的地理位置分布情况",
            category="distribution",
            status="pending",
            create_time=datetime.now(),
        ),
        TaskRecommendationResponse(
            id=3,
            session_id=session_id,
            title="活跃用户对比",
            description="对比不同时段的活跃用户数量",
            category="comparison",
            status="pending",
            create_time=datetime.now(),
        ),
    ]

    return BaseResponse(
        success=True,
        code=200,
        msg="获取推荐列表成功",
        data=mock_recommendations,
    )


@router.post("/recommendations/{recommendation_id}/select", response_model=BaseResponse[ChatMessageResponse])
async def select_recommendation(
    session_id: int,
    recommendation_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """选择一个推荐任务执行"""
    # 验证会话权限
    service = AnalysisSessionService(db)
    await service.get_session(session_id, current_user.id)

    # Mock: 将推荐转换为用户消息
    mock_message = ChatMessageResponse(
        id=random.randint(100, 999),
        session_id=session_id,
        role=MessageRole.USER,
        message_type=MessageType.TEXT,
        content="分析用户增长趋势",  # 实际应从推荐中获取
        create_time=datetime.now(),
    )

    return BaseResponse(
        success=True,
        code=200,
        msg="已选择推荐任务",
        data=mock_message,
    )
