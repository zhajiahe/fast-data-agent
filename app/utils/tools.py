from typing import Any

import httpx
from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.core.config import settings


class DataSourceContext(BaseModel):
    """数据源上下文信息"""

    id: int
    name: str
    source_type: str  # "file" 或 "database"

    # 文件类型
    file_type: str | None = None
    object_key: str | None = None
    bucket_name: str | None = None

    # 数据库类型
    db_type: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None


class ChatContext(BaseModel):
    """聊天上下文 - 包含运行时配置和数据源信息"""

    user_id: int
    thread_id: int
    data_sources: list[DataSourceContext] = Field(default_factory=list)


# ==================== 工具定义 ====================


@tool
async def list_local_files(runtime: ToolRuntime) -> Any:
    """
    列出沙盒中的文件。
    用于查看分析过程中生成的中间文件、图表、报告等。
    """
    runtime.stream_writer("正在获取文件列表...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]
    params = {
        "user_id": ctx.user_id,
        "thread_id": ctx.thread_id,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{settings.SANDBOX_URL}/files",
            params=params,
        )
        return response.json()


@tool
async def quick_analysis(
    data_source_id: int,
    runtime: ToolRuntime,
) -> Any:
    """
    快速分析数据源，返回数据概览。
    支持文件类型（CSV/Excel/JSON/Parquet）和数据库类型（MySQL/PostgreSQL/SQLite）。

    对于文件类型：返回行数、列数、缺失值统计、数据类型、统计摘要。
    对于数据库类型：返回表列表、每个表的行数和列信息。

    Args:
        data_source_id: 数据源 ID，从可用数据源列表中选择
    """
    runtime.stream_writer(f"正在分析数据源 {data_source_id}...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    # 从 context 中查找数据源
    ds_ctx: DataSourceContext | None = None
    for ds in ctx.data_sources:
        if ds.id == data_source_id:
            ds_ctx = ds
            break

    if ds_ctx is None:
        return {"success": False, "error": f"数据源 {data_source_id} 不在当前会话的可用数据源列表中"}

    # 构建数据源信息传递给沙盒
    data_source_info: dict[str, Any] = {
        "source_type": ds_ctx.source_type,
    }

    if ds_ctx.source_type == "file":
        data_source_info.update(
            {
                "file_type": ds_ctx.file_type,
                "object_key": ds_ctx.object_key,
                "bucket_name": ds_ctx.bucket_name,
            }
        )
    elif ds_ctx.source_type == "database":
        data_source_info.update(
            {
                "db_type": ds_ctx.db_type,
                "host": ds_ctx.host,
                "port": ds_ctx.port,
                "database": ds_ctx.database,
                "username": ds_ctx.username,
                "password": ds_ctx.password,
            }
        )

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{settings.SANDBOX_URL}/quick_analysis",
            params={
                "user_id": ctx.user_id,
                "thread_id": ctx.thread_id,
            },
            json={"data_source": data_source_info},
        )
        result = response.json()

        # 添加数据源名称到结果中
        if result.get("success") and result.get("analysis"):
            result["analysis"]["data_source_name"] = ds_ctx.name
            result["analysis"]["data_source_id"] = ds_ctx.id

        return result


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
    code: str,
    runtime: ToolRuntime,
) -> Any:
    """
    生成 Plotly 图表。
    使用 Plotly 生成图表，并返回图表的 HTML 代码。
    Args:
        code: 使用 Plotly 生成图表的 Python 代码
    """
    runtime.stream_writer("正在生成图表...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.SANDBOX_URL}/generate_chart",
            params={
                "user_id": ctx.user_id,
                "thread_id": ctx.thread_id,
            },
            json={
                "code": code,
            },
        )
        return response.json()
