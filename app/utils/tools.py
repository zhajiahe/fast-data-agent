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


class RawDataContext(BaseModel):
    """原始数据上下文信息"""

    id: int
    name: str
    raw_type: str  # "database_table" 或 "file"

    # 文件类型
    file_type: str | None = None
    object_key: str | None = None
    bucket_name: str | None = None

    # 数据库表类型
    connection_id: int | None = None
    db_type: str | None = None
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    schema_name: str | None = None
    table_name: str | None = None


class DataSourceContext(BaseModel):
    """数据源上下文信息"""

    id: int
    name: str
    description: str | None = None
    category: str | None = None

    # 关联的原始数据
    raw_data_list: list[RawDataContext] = Field(default_factory=list)

    # 目标字段定义
    target_fields: list[dict[str, Any]] | None = None


class ChatContext(BaseModel):
    """聊天上下文 - 包含运行时配置和数据源信息"""

    user_id: int
    thread_id: int
    data_source: DataSourceContext | None = None


# ==================== 错误处理工具 ====================


def extract_error_for_llm(error_text: str, max_lines: int = 10) -> str:
    """
    从错误信息中提取对 LLM 有价值的关键行。
    保留: 错误类型、错误消息、Did you mean 建议、KeyError 等。
    过滤: 完整的 traceback 堆栈。
    """
    if not error_text:
        return "未知错误"

    lines = error_text.split("\n")
    key_lines: list[str] = []
    keywords = ("error", "exception", "did you mean", "keyerror", "invalid", "not found", "不存在")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # 跳过 traceback 的堆栈行（File "...", line ...）
        if stripped.startswith("File ") and ", line " in stripped:
            continue
        # 跳过纯缩进的代码行
        if line.startswith("    ") and not any(kw in stripped.lower() for kw in keywords):
            continue
        # 保留关键信息行
        if any(kw in stripped.lower() for kw in keywords) or len(key_lines) < 3:
            key_lines.append(stripped)

    # 限制最大行数
    result = "\n".join(key_lines[:max_lines])
    return result if result else error_text.split("\n")[0]


# ==================== 工具定义 ====================


@tool(response_format="content_and_artifact")
async def list_local_files(runtime: ToolRuntime) -> tuple[str, dict[str, Any]]:
    """
    列出沙盒中的文件。
    用于查看分析过程中生成的中间文件、图表、报告等。

    Returns:
        content: 文件列表摘要（给 LLM）
        artifact: 完整文件列表（给前端）
    """
    runtime.stream_writer("正在获取文件列表...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]
    params = {
        "user_id": ctx.user_id,
        "thread_id": ctx.thread_id,
    }
    client = get_sandbox_client()
    response = await client.get("/files", params=params)
    result = response.json()

    files = result.get("files", [])
    if not files:
        return "当前会话目录为空，暂无文件。", {"type": "file_list", "files": []}

    # 给 LLM 的文件列表摘要
    content_lines = [f"会话目录中共有 {len(files)} 个文件："]
    for f in files[:10]:  # 最多显示 10 个
        name = f.get("name", "")
        size = f.get("size", 0)
        size_str = f"{size / 1024:.1f}KB" if size >= 1024 else f"{size}B"
        content_lines.append(f"  - {name} ({size_str})")
    if len(files) > 10:
        content_lines.append(f"  ...等共 {len(files)} 个文件")

    return "\n".join(content_lines), {"type": "file_list", "files": files}


@tool(response_format="content_and_artifact")
async def quick_analysis(
    runtime: ToolRuntime,
    file_name: str = "",
) -> tuple[str, dict[str, Any]]:
    """
    快速分析数据，返回数据概览和统计摘要。

    支持两种模式：
    1. 分析数据源 VIEW：file_name 为空时，分析当前会话绑定的数据源
    2. 分析会话文件：file_name 指定时，分析会话目录中的文件（如 sql_result_xxx.parquet）

    Args:
        file_name: 可选，要分析的会话文件名（如 'sql_result_abcd.parquet'）。
                   留空则分析数据源 VIEW。

    Returns:
        content: 格式化的分析摘要（给 LLM）
        artifact: 完整分析结果（给前端）
    """
    ctx: ChatContext = runtime.context  # type: ignore[assignment]
    client = get_sandbox_client()

    # 模式 1：分析会话文件
    if file_name:
        runtime.stream_writer(f"正在分析文件: {file_name}...")
        response = await client.post(
            "/quick_analysis",
            params={
                "user_id": ctx.user_id,
                "thread_id": ctx.thread_id,
            },
            json={"file_name": file_name},
        )
        result = response.json()

        if not result.get("success"):
            error_msg = result.get("error", "分析失败")
            return f"文件分析失败: {error_msg}", {"type": "error", "error": error_msg}

        analysis = result.get("analysis", {})

        # 构建格式化的分析摘要
        content_lines = [f"## 文件: {file_name}"]
        content_lines.append(f"- 行数: {analysis.get('row_count', 'N/A')}")
        content_lines.append(f"- 列数: {analysis.get('column_count', 'N/A')}")

        # 列信息
        columns = analysis.get("columns", [])
        if columns:
            content_lines.append("\n### 列信息:")
            for col in columns[:15]:
                col_name = col.get("name", "")
                col_type = col.get("dtype", "")
                null_count = col.get("null_count", 0)
                null_info = f", 缺失 {null_count}" if null_count > 0 else ""
                content_lines.append(f"  - {col_name} ({col_type}{null_info})")
            if len(columns) > 15:
                content_lines.append(f"  ...等共 {len(columns)} 列")

        # 数值统计摘要
        numeric_cols = [c for c in columns if c.get("stats")]
        if numeric_cols:
            content_lines.append("\n### 数值统计摘要:")
            for col in numeric_cols[:5]:
                col_name = col.get("name", "")
                stats = col.get("stats", {})

                def _fmt_num(value: Any) -> str:
                    return f"{value:.2f}" if isinstance(value, (int, float)) else str(value)

                content_lines.append(
                    f"  - {col_name}: 均值={_fmt_num(stats.get('mean', 'N/A'))}, "
                    f"范围=[{_fmt_num(stats.get('min', 'N/A'))}, {_fmt_num(stats.get('max', 'N/A'))}]"
                )

        artifact = {
            "type": "analysis",
            "file_name": file_name,
            **analysis,
        }
        return "\n".join(content_lines), artifact

    # 模式 2：分析数据源 VIEW
    runtime.stream_writer("正在分析数据源...")

    # 从 context 获取数据源
    ds_ctx = ctx.data_source
    if ds_ctx is None:
        error_msg = "当前会话没有关联数据源"
        return error_msg, {"type": "error", "error": error_msg}

    if not ds_ctx.raw_data_list:
        error_msg = f"数据源 {ds_ctx.name} 没有关联的原始数据"
        return error_msg, {"type": "error", "error": error_msg}

    # 提取所有 RawData 的名称作为 VIEW 名称
    view_names = [raw.name for raw in ds_ctx.raw_data_list]

    response = await client.post(
        "/quick_analysis",
        params={
            "user_id": ctx.user_id,
            "thread_id": ctx.thread_id,
        },
        json={"view_names": view_names},
    )
    result = response.json()

    if not result.get("success"):
        error_msg = result.get("error", "分析失败")
        return f"数据源分析失败: {error_msg}", {"type": "error", "error": error_msg}

    analysis = result.get("analysis", {})

    # 构建格式化的分析摘要（给 LLM）
    content_lines = [f"## 数据源: {ds_ctx.name} (ID: {ds_ctx.id})"]

    # 处理多 VIEW 的情况
    views = analysis.get("views", [analysis])  # 单 VIEW 时 analysis 本身就是结果
    for view_analysis in views:
        view_name = view_analysis.get("view_name", view_names[0] if view_names else "unknown")

        if "error" in view_analysis:
            content_lines.append(f"\n### VIEW: {view_name}")
            content_lines.append(f"  ⚠️ 分析失败: {view_analysis['error']}")
            continue

        content_lines.append(f"\n### VIEW: {view_name}")
        content_lines.append(f"- 行数: {view_analysis.get('row_count', 'N/A')}")
        content_lines.append(f"- 列数: {view_analysis.get('column_count', 'N/A')}")

    # 列信息
        columns = view_analysis.get("columns", [])
    if columns:
            content_lines.append("\n#### 列信息:")
        for col in columns[:15]:  # 最多显示 15 列
            col_name = col.get("name", "")
            col_type = col.get("dtype", "")
            null_count = col.get("null_count", 0)
            null_info = f", 缺失 {null_count}" if null_count > 0 else ""
            content_lines.append(f"  - {col_name} ({col_type}{null_info})")
        if len(columns) > 15:
            content_lines.append(f"  ...等共 {len(columns)} 列")

        # 数值统计摘要（从 columns 中提取）
        numeric_cols = [c for c in columns if c.get("stats")]
        if numeric_cols:
            content_lines.append("\n#### 数值统计摘要:")
            for col in numeric_cols[:5]:  # 最多显示 5 列
                col_name = col.get("name", "")
                stats = col.get("stats", {})
                mean_val = stats.get("mean", "N/A")
                min_val = stats.get("min", "N/A")
                max_val = stats.get("max", "N/A")

            def _fmt_num(value: Any) -> str:
                """安全格式化，避免非数值类型导致格式化异常。"""
                return f"{value:.2f}" if isinstance(value, (int, float)) else str(value)

            content_lines.append(
                f"  - {col_name}: 均值={_fmt_num(mean_val)}, 范围=[{_fmt_num(min_val)}, {_fmt_num(max_val)}]"
            )

    # 告诉 LLM 可用的 VIEW 名称（用于后续 SQL 查询）
    content_lines.append(f"\n💡 **可用 VIEW**: {', '.join(view_names)}")
    content_lines.append("使用 `execute_sql` 工具时，可直接用这些 VIEW 名称作为表名查询。")

    # artifact 包含完整分析结果
    artifact = {
        "type": "analysis",
        "data_source_name": ds_ctx.name,
        "data_source_id": ds_ctx.id,
        "available_views": view_names,
        **analysis,
    }

    return "\n".join(content_lines), artifact


@tool(
    response_format="content_and_artifact",
    description="""使用 DuckDB SQL 方言查询数据。
**数据访问方式**：
1. 数据源 VIEW：使用 RawData 名称（会话初始化时自动创建）
   - `SELECT * FROM "pg_orders" LIMIT 10`
   - `SELECT * FROM "sales_csv"`
2. 会话目录文件：直接读取本地文件
   - CSV: `SELECT * FROM read_csv_auto('file.csv')`
   - Parquet: `SELECT * FROM 'file.parquet'`
   - JSON: `SELECT * FROM read_json_auto('file.json')`

**示例**：
- 查询 VIEW：`SELECT category, SUM(amount) FROM "pg_orders" GROUP BY category`
- 读取上次结果：`SELECT * FROM 'sql_result_xxx.parquet' WHERE amount > 1000`

**重要**：结果自动保存为 parquet 文件（result_file），供后续工具使用""",
)
async def execute_sql(
    sql: str,
    runtime: ToolRuntime,
) -> tuple[str, dict[str, Any]]:
    """
    执行 DuckDB SQL 查询。
    查询会话 DuckDB 中的 VIEWs（以 RawData 名称命名）。

    Args:
        sql: DuckDB SQL 查询，表名使用 RawData 名称

    Returns:
        content: 给 LLM 看的简短描述
        artifact: 包含 SQL 和查询结果的字典（前端渲染用）
    """
    runtime.stream_writer("正在执行 SQL 查询...")
    ctx: ChatContext = runtime.context  # type: ignore[assignment]

    client = get_sandbox_client()
    response = await client.post(
        "/execute_sql",
        params={
            "user_id": ctx.user_id,
            "thread_id": ctx.thread_id,
        },
        json={"sql": sql},
    )
    result = response.json()

    # 从 context 获取可用 VIEW 列表
    available_views: list[str] = []
    if ctx.data_source and ctx.data_source.raw_data_list:
        available_views = [raw.name for raw in ctx.data_source.raw_data_list]

    if result.get("success"):
        row_count = result.get("row_count", 0)
        columns = result.get("columns", [])
        result_file = result.get("result_file", "")
        rows = result.get("rows", [])

        # 构建给 LLM 的内容
        content_lines = [
            "✅ SQL 查询成功",
            f"- 返回 {row_count} 行数据",
            f"- 结果已保存至: {result_file}",
            f"- 列名: {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}",
        ]

        # 显示前 10 行数据预览（给 LLM 参考）
        if rows:
            content_lines.append("\n📊 数据预览 (前 10 行):")
            preview_rows = rows[:10]
            # 构建简单的表格格式
            for i, row in enumerate(preview_rows):
                row_str = " | ".join(str(v)[:20] for v in row)  # 每个值最多 20 字符
                content_lines.append(f"  {i + 1}. {row_str}")
            if row_count > 10:
                content_lines.append(f"  ...共 {row_count} 行，完整数据请在前端查看")

        # artifact 包含更多数据（给前端渲染）
        max_rows_for_frontend = 100
        artifact = {
            "type": "sql",
            "sql": sql,
            "columns": columns,
            "rows": rows[:max_rows_for_frontend],
            "total_rows": row_count,
            "truncated": len(rows) > max_rows_for_frontend,
            "result_file": result_file,
            "available_views": available_views,
        }
        return "\n".join(content_lines), artifact
    else:
        error_detail = result.get("error", "未知错误")
        # 给 LLM 关键错误信息（便于反思和修正）
        error_for_llm = extract_error_for_llm(error_detail)

        # 在错误信息中提示可用的 VIEW 列表，帮助 LLM 修正 SQL
        content_lines = [f"❌ SQL 执行失败:\n{error_for_llm}"]
        if available_views:
            content_lines.append(f"\n💡 **可用 VIEW**: {', '.join(available_views)}")
            content_lines.append("请检查表名是否正确，VIEW 名称需要用双引号包裹。")

        return "\n".join(content_lines), {
            "type": "error",
            "tool": "execute_sql",
            "sql": sql,
            "error_message": error_detail,  # 完整错误信息（给前端调试用）
            "available_views": available_views,
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

        # 构建给 LLM 的内容
        content_lines = ["✅ Python 代码执行成功"]

        if output:
            # 显示输出预览（最多 500 字符）
            output_preview = output[:500]
            content_lines.append(f"\n📝 输出:\n{output_preview}")
            if len(output) > 500:
                content_lines.append("...(输出已截断，完整输出请在前端查看)")

        if files_created:
            content_lines.append(f"\n📁 生成文件: {', '.join(files_created)}")

        artifact = {
            "type": "code",
            "code": code,
            "output": output,
            "files_created": files_created,
        }
        return "\n".join(content_lines), artifact
    else:
        error_detail = result.get("error", "未知错误")
        output = result.get("output", "")
        # 给 LLM 关键错误信息（便于反思和修正）
        error_for_llm = extract_error_for_llm(error_detail)
        content = f"❌ Python 执行失败:\n{error_for_llm}"
        return content, {
            "type": "error",
            "tool": "execute_python",
            "code": code,
            "output": output,  # 执行时的标准输出
            "error_message": error_detail,  # 完整错误信息（给前端调试用）
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
    title: str,
    runtime: ToolRuntime,
) -> tuple[str, dict[str, Any]]:
    """
    生成 Plotly 图表。
    使用 Plotly 生成图表，代码需要创建名为 'fig' 的 Plotly figure 对象。

    Args:
        code: 使用 Plotly 生成图表的 Python 代码，必须创建 fig 变量
        title: 图表标题，用于在前端显示

    Returns:
        content: 给 LLM 看的简短描述
        artifact: 包含完整图表数据的字典（不发送给 LLM）
    """
    runtime.stream_writer(f"正在生成图表: {title}...")
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
        content_lines = [
            f"✅ 图表「{title}」生成成功",
            "📊 图表数据已发送至前端渲染",
            "💡 用户可以在聊天界面直接查看交互式 Plotly 图表",
        ]

        # artifact: 完整图表数据（给前端渲染）
        artifact = {
            "type": "plotly",
            "title": title,
            "chart_json": result.get("chart_json"),  # Plotly JSON 数据
        }
        return "\n".join(content_lines), artifact
    else:
        error_detail = result.get("error", "未知错误")
        output = result.get("output", "")
        # 给 LLM 关键错误信息（便于反思和修正）
        error_for_llm = extract_error_for_llm(error_detail)
        content = f"❌ 图表「{title}」生成失败:\n{error_for_llm}"
        return content, {
            "type": "error",
            "tool": "generate_chart",
            "title": title,
            "code": code,
            "output": output,
            "error_message": error_detail,  # 完整错误信息（给前端调试用）
        }
