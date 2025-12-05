from typing import Any

import httpx
from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.core.config import settings

# ==================== HTTP 客户端连接池 ====================


class SandboxHttpClient:
    """
    沙盒 HTTP 客户端管理器
    - 复用 HTTP 连接，减少连接建立开销
    - 支持连接池
    """

    _client: httpx.AsyncClient | None = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                base_url=settings.SANDBOX_URL,
                timeout=settings.SANDBOX_TIMEOUT,
                # 连接池配置
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0,
                ),
            )
        return cls._client

    @classmethod
    async def close(cls) -> None:
        """关闭 HTTP 客户端"""
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            cls._client = None


# 快捷访问函数
def get_sandbox_client() -> httpx.AsyncClient:
    """获取沙盒 HTTP 客户端"""
    return SandboxHttpClient.get_client()


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
    client = get_sandbox_client()
    response = await client.get("/files", params=params)
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

    client = get_sandbox_client()
    response = await client.post(
        "/quick_analysis",
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


@tool(
    response_format="content_and_artifact",
    description="""使用 DuckDB SQL 方言查询数据。
**数据源访问方式**：
1. 会话数据源：使用数据源名称或 ds_ID
   - `SELECT * FROM "电商订单数据" LIMIT 10`
   - `SELECT * FROM ds_19`
2. 本地文件：直接读取会话目录中的文件
   - CSV: `SELECT * FROM read_csv_auto('file.csv')`
   - Parquet: `SELECT * FROM 'file.parquet'`
   - JSON: `SELECT * FROM read_json_auto('file.json')`

**示例**：
- 查询数据源：`SELECT category, SUM(amount) FROM "电商订单数据" GROUP BY category`
- 读取上次结果：`SELECT * FROM 'sql_result_xxx.parquet' WHERE amount > 1000`

**重要**：结果自动保存为 parquet 文件（result_file），供后续工具使用""",
)
async def execute_sql(
    sql: str,
    runtime: ToolRuntime,
) -> tuple[str, dict[str, Any]]:
    """
    执行 DuckDB SQL 查询。
    支持对会话中所有数据源进行 SQL 查询分析。

    Args:
        sql: duckdb sql query，表名使用数据源名称或 ds_{id} 格式

    Returns:
        content: 给 LLM 看的简短描述
        artifact: 包含 SQL 和查询结果的字典（前端渲染用）
    """
    runtime.stream_writer("正在执行 SQL 查询...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    # 构建数据源信息列表传递给沙盒
    data_sources_info = []
    for ds in ctx.data_sources:
        ds_info: dict[str, Any] = {
            "id": ds.id,
            "name": ds.name,
            "source_type": ds.source_type,
        }
        if ds.source_type == "file":
            ds_info.update(
                {
                    "file_type": ds.file_type,
                    "object_key": ds.object_key,
                    "bucket_name": ds.bucket_name,
                }
            )
        data_sources_info.append(ds_info)

    client = get_sandbox_client()
    response = await client.post(
        "/execute_sql",
        params={
            "user_id": ctx.user_id,
            "thread_id": ctx.thread_id,
        },
        json={
            "sql": sql,
            "data_sources": data_sources_info,
        },
    )
    result = response.json()

    if result.get("success"):
        row_count = result.get("row_count", 0)
        content = f"查询成功，返回 {row_count} 行数据"

        # 限制 artifact 中的行数，避免数据过大
        rows = result.get("rows", [])
        max_rows = 100
        artifact = {
            "type": "sql",
            "sql": sql,
            "columns": result.get("columns", []),
            "rows": rows[:max_rows],
            "total_rows": row_count,
            "truncated": len(rows) > max_rows,
            "result_file": result.get("result_file"),
        }
        return content, artifact
    else:
        error_detail = result.get("error", "未知错误")
        # 给 LLM 简短摘要
        error_summary = error_detail.split("\n")[0] if error_detail else "未知错误"
        content = f"SQL 执行失败: {error_summary}"
        return content, {
            "type": "error",
            "tool": "execute_sql",
            "sql": sql,
            "error_message": error_detail,  # 完整错误信息（含 traceback）
        }


@tool(
    response_format="content_and_artifact",
    description="""执行 Python 代码进行数据处理。
**最佳实践**：
如果你正在清洗数据以便绘图，请务必将最终的 DataFrame 保存为文件。
- 推荐格式：`df.to_parquet('analysis_result.parquet')`
- 这样你就可以在 `generate_chart` 工具中通过 `pd.read_parquet('analysis_result.parquet')` 快速复用数据。""",
)
async def execute_python(
    code: str,
    runtime: ToolRuntime,
) -> tuple[str, dict[str, Any]]:
    """
    在沙盒中执行 Python 代码，用于复杂数据处理和分析。
    可以使用 pandas、numpy 等数据分析库。

    Args:
        code: 要执行的 Python 代码

    Returns:
        content: 给 LLM 看的简短描述
        artifact: 包含代码和执行结果的字典（前端渲染用）
    """
    runtime.stream_writer("正在执行 Python 代码...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    client = get_sandbox_client()
    response = await client.post(
        "/execute_python",
        params={
            "user_id": ctx.user_id,
            "thread_id": ctx.thread_id,
        },
        json={"code": code},
    )
    result = response.json()

    if result.get("success"):
        output = result.get("output", "")
        files_created = result.get("files_created", [])
        # 给 LLM 的简短描述
        content = output[:500] if output else "代码执行成功"
        if files_created:
            content += f"\n生成文件: {', '.join(files_created)}"

        artifact = {
            "type": "code",
            "code": code,
            "output": output,
            "files_created": files_created,
        }
        return content, artifact
    else:
        error_detail = result.get("error", "未知错误")
        output = result.get("output", "")
        # 给 LLM 简短摘要
        error_summary = error_detail.split("\n")[0] if error_detail else "未知错误"
        content = f"Python 执行失败: {error_summary}"
        return content, {
            "type": "error",
            "tool": "execute_python",
            "code": code,
            "output": output,  # 执行时的标准输出
            "error_message": error_detail,  # 完整错误信息（含 traceback）
        }


@tool(
    response_format="content_and_artifact",
    description="""使用 Python Plotly 绘制图表。

**关键策略 - 数据复用**：
直接读取 execute_sql 自动保存的结果文件（result_file 字段中的文件名）。

**代码编写规范**：
1. **加载数据**：使用 `pd.read_parquet('sql_result_xxx.parquet')` 读取 SQL 结果文件
2. **定义对象**：必须创建一个名为 `fig` 的 Plotly Figure 对象
3. **禁止显示**：不要调用 `fig.show()`

**示例**：
```python
import pandas as pd
import plotly.express as px
df = pd.read_parquet('sql_result_1234567890.parquet')  # 使用 execute_sql 返回的 result_file
fig = px.bar(df, x='category', y='total_sales', title='销售额分布')
```""",
)
async def generate_chart(
    code: str,
    runtime: ToolRuntime,
) -> tuple[str, dict[str, Any]]:
    """
    生成 Plotly 图表。
    使用 Plotly 生成图表，代码需要创建名为 'fig' 的 Plotly figure 对象。

    Args:
        code: 使用 Plotly 生成图表的 Python 代码，必须创建 fig 变量

    Returns:
        content: 给 LLM 看的简短描述
        artifact: 包含完整图表数据的字典（不发送给 LLM）
    """
    runtime.stream_writer("正在生成图表...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    client = get_sandbox_client()
    response = await client.post(
        "/generate_chart",
        params={
            "user_id": ctx.user_id,
            "thread_id": ctx.thread_id,
        },
        json={
            "code": code,
        },
    )
    result = response.json()

    if result.get("success"):
        # content: 给 LLM 的简短描述
        content = f"图表已生成并保存为 {result.get('chart_file', 'chart.html')}"

        # artifact: 完整图表数据，不发送给 LLM
        artifact = {
            "type": "plotly",
            "chart_file": result.get("chart_file"),
            "chart_json": result.get("chart_json"),  # 完整的 Plotly JSON
        }
        return content, artifact
    else:
        error_detail = result.get("error", "未知错误")
        output = result.get("output", "")
        # 给 LLM 简短摘要
        error_summary = error_detail.split("\n")[0] if error_detail else "未知错误"
        content = f"图表生成失败: {error_summary}"
        return content, {
            "type": "error",
            "tool": "generate_chart",
            "code": code,
            "output": output,
            "error_message": error_detail,  # 完整错误信息（含 traceback）
        }
