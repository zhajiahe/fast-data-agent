# Copyright 2025 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
沙箱运行时主模块

提供安全的代码执行、SQL 查询、文件管理等 API。
"""

import io
import logging
import os
import subprocess
import sys
import traceback
from contextlib import asynccontextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

# 从模块导入
from sandbox_runtime.models import (
    ChartRequest,
    CodeExecutionResult,
    CodeRequest,
    ExecuteRequest,
    ExecuteResponse,
    InitSessionRequest,
    QuickAnalysisRequest,
    SqlRequest,
)
from sandbox_runtime.services import (
    FileService,
    analyze_data_with_duckdb,
    configure_s3_access,
    duckdb_manager,
)
from sandbox_runtime.utils import (
    SANDBOX_ROOT,
    ensure_session_dir,
    generate_unique_filename,
    get_session_dir,
    list_files_in_dir,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 应用生命周期 ====================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    Startup:
    - 预加载 DuckDB 扩展（httpfs、postgres、mysql 等）
    - 确保扩展目录存在

    Shutdown:
    - 清理临时资源（如有）
    """
    # ===== Startup =====
    logger.info("🚀 Sandbox Runtime 启动中...")

    # 预加载 DuckDB 扩展
    duckdb_manager.preload_extensions()

    # 确保 sessions 目录存在
    sessions_dir = SANDBOX_ROOT / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    logger.info("✅ Sandbox Runtime 启动完成")

    yield  # 应用运行中

    # ===== Shutdown =====
    logger.info("🛑 Sandbox Runtime 关闭中...")
    # 目前没有需要清理的资源
    logger.info("👋 Sandbox Runtime 已关闭")


# ==================== FastAPI App ====================


app = FastAPI(
    title="Agentic Sandbox Runtime",
    description="An API server for executing commands and managing files in a secure sandbox.",
    version="2.0.0",
    lifespan=lifespan,
)


# ==================== 健康检查 ====================


@app.get("/health", summary="Health Check")
async def health_check():
    """A simple health check endpoint to confirm the server is running."""
    return {"status": "ok", "message": "Sandbox Runtime is active."}


# ==================== 会话初始化 ====================


@app.get("/list_views", summary="List available VIEWs in session DuckDB")
async def list_views(
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    列出会话 DuckDB 中所有可用的 VIEW。

    返回每个 VIEW 的名称、列信息和行数。
    用于让 AI 知道当前可以查询哪些数据。
    """
    import duckdb

    session_dir = get_session_dir(user_id, thread_id)
    duckdb_path = session_dir / "session.duckdb"

    if not duckdb_path.exists():
        return {
            "success": True,
            "views": [],
            "message": "Session DuckDB not initialized",
        }

    try:
        conn = duckdb.connect(str(duckdb_path), read_only=True)

        # 设置扩展目录
        extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
        conn.execute(f"SET extension_directory='{extensions_dir}';")

        # 配置 S3 访问（VIEW 可能引用 S3 URL）
        configure_s3_access(conn)

        # 查询所有 VIEW
        views_result = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
        ).fetchall()

        views_info = []
        for (view_name,) in views_result:
            try:
                # 获取列信息
                columns_meta = conn.execute(f'PRAGMA table_info("{view_name}")').fetchall()
                columns = [{"name": col[1], "dtype": col[2]} for col in columns_meta]

                # 尝试获取行数（可能因为外部连接问题失败）
                try:
                    row_count = conn.execute(f'SELECT COUNT(*) FROM "{view_name}"').fetchone()[0]
                except Exception:
                    row_count = None  # 外部数据源可能不可达

                views_info.append(
                    {
                        "name": view_name,
                        "columns": columns,
                        "column_count": len(columns),
                        "row_count": row_count,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to get info for view {view_name}: {e}")
                views_info.append(
                    {
                        "name": view_name,
                        "error": str(e),
                    }
                )

        conn.close()

        return {
            "success": True,
            "views": views_info,
            "view_count": len(views_info),
        }

    except Exception as e:
        logger.exception(f"Failed to list views: {e}")
        return {"success": False, "error": str(e), "views": []}


@app.post("/init_session", summary="Initialize session DuckDB with raw data")
async def init_session(
    request: InitSessionRequest,
    user_id: str = Query(..., description="User ID (UUID string)"),
    thread_id: str = Query(..., description="Thread/Session ID (UUID string)"),
):
    """
    初始化会话的 DuckDB 文件。

    创建一个持久化的 DuckDB 文件，并根据数据对象配置：
    - 安装并加载必要的扩展 (postgres, mysql, httpfs)
    - ATTACH 外部数据库
    - 为每个 RawData 创建 VIEW
    """
    import duckdb

    session_dir = ensure_session_dir(user_id, thread_id)
    duckdb_path = session_dir / "session.duckdb"

    try:
        # 创建/打开 DuckDB 文件
        conn = duckdb.connect(str(duckdb_path))

        # 设置扩展目录
        extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
        extensions_dir.mkdir(parents=True, exist_ok=True)
        conn.execute(f"SET extension_directory='{extensions_dir}';")

        views_created: list[str] = []
        errors: list[str] = []

        # 如果没有数据对象，只创建空的 DuckDB 文件
        if not request.raw_data_list:
            conn.close()
            return {
                "success": True,
                "message": "Session DuckDB initialized (no raw data)",
                "duckdb_path": str(duckdb_path),
                "views_created": [],
                "errors": [],
            }

        # 为每个 RawData 创建 VIEW
        for raw_data in request.raw_data_list:
            try:
                view_name = raw_data.name  # 使用 RawData 名称作为 VIEW 名称

                if raw_data.raw_type == "database_table":
                    # 数据库表类型：ATTACH 数据库并创建 VIEW
                    if raw_data.db_type == "postgresql":
                        conn.execute("INSTALL postgres; LOAD postgres;")
                        conn_str = (
                            f"host={raw_data.host} "
                            f"port={raw_data.port} "
                            f"dbname={raw_data.database} "
                            f"user={raw_data.username} "
                            f"password={raw_data.password}"
                        )
                        attach_name = f"pg_{raw_data.id}"
                        conn.execute(f"ATTACH '{conn_str}' AS {attach_name} (TYPE POSTGRES, READ_ONLY);")

                        # 构建源表名
                        if raw_data.custom_sql:
                            # 使用自定义 SQL
                            conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS {raw_data.custom_sql}')
                        else:
                            # 使用 schema.table
                            schema = raw_data.schema_name or "public"
                            table = raw_data.table_name
                            conn.execute(
                                f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM {attach_name}.{schema}.{table}'
                            )

                    elif raw_data.db_type == "mysql":
                        conn.execute("INSTALL mysql; LOAD mysql;")
                        conn_str = (
                            f"host={raw_data.host} "
                            f"port={raw_data.port} "
                            f"database={raw_data.database} "
                            f"user={raw_data.username} "
                            f"password={raw_data.password}"
                        )
                        attach_name = f"mysql_{raw_data.id}"
                        conn.execute(f"ATTACH '{conn_str}' AS {attach_name} (TYPE MYSQL, READ_ONLY);")

                        if raw_data.custom_sql:
                            conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS {raw_data.custom_sql}')
                        else:
                            table = raw_data.table_name
                            conn.execute(
                                f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM {attach_name}.{table}'
                            )

                    views_created.append(view_name)

                elif raw_data.raw_type == "file":
                    # 文件类型：通过 S3/httpfs 创建 VIEW
                    configure_s3_access(conn)

                    s3_url = f"s3://{raw_data.bucket_name}/{raw_data.object_key}"

                    if raw_data.file_type == "csv":
                        conn.execute(
                            f"CREATE OR REPLACE VIEW \"{view_name}\" AS SELECT * FROM read_csv_auto('{s3_url}', header=True)"
                        )
                    elif raw_data.file_type == "parquet":
                        conn.execute(
                            f"CREATE OR REPLACE VIEW \"{view_name}\" AS SELECT * FROM parquet_scan('{s3_url}')"
                        )
                    elif raw_data.file_type == "json":
                        conn.execute(
                            f"CREATE OR REPLACE VIEW \"{view_name}\" AS SELECT * FROM read_json_auto('{s3_url}')"
                        )
                    elif raw_data.file_type == "excel":
                        conn.execute("INSTALL spatial; LOAD spatial;")
                        conn.execute(f"CREATE OR REPLACE VIEW \"{view_name}\" AS SELECT * FROM st_read('{s3_url}')")

                    views_created.append(view_name)

            except Exception as e:
                error_msg = f"Failed to create view for {raw_data.name}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)

        conn.close()

        logger.info(f"Session DuckDB initialized: user_id={user_id}, thread_id={thread_id}, views={len(views_created)}")

        return {
            "success": True,
            "message": f"Session DuckDB initialized with {len(views_created)} views",
            "duckdb_path": str(duckdb_path),
            "views_created": views_created,
            "errors": errors,
        }

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.exception(f"Failed to initialize session DuckDB: {e}")
        return {"success": False, "error": f"{str(e)}\n\n{error_traceback}"}


# ==================== 重置操作 ====================


@app.post("/reset/session", summary="Reset session files")
async def reset_session(
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    重置指定会话的文件。
    删除该会话目录下的所有文件。
    """
    return FileService.reset_session(user_id, thread_id)


@app.post("/reset/user", summary="Reset all user sessions")
async def reset_user(
    user_id: str = Query(..., description="User ID"),
):
    """
    重置指定用户的所有会话文件。
    删除该用户目录下的所有文件。
    """
    return FileService.reset_user(user_id)


@app.post("/reset/all", summary="Reset all sandbox data")
async def reset_all():
    """
    重置所有沙盒数据。
    删除 sessions 目录下的所有文件。
    仅用于管理目的，谨慎使用。
    """
    return FileService.reset_all()


# ==================== 文件管理 ====================


@app.get("/files", summary="List files in session directory")
async def list_files(
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    列出会话目录中的所有文件。
    用于查看分析过程中生成的中间文件、图表、报告等。
    """
    files = FileService.list_session_files(user_id, thread_id)

    return {
        "success": True,
        "files": files,
        "count": len(files),
    }


@app.post("/upload", summary="Upload a file to the session directory")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    上传文件到会话目录。
    用户无需关心具体存储路径，文件自动保存到对应会话目录。
    """
    try:
        content = await file.read()
        file_path = FileService.save_uploaded_file(user_id, thread_id, file.filename, content)
        session_dir = get_session_dir(user_id, thread_id)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"File '{file.filename}' uploaded successfully.",
                "path": str(file_path.relative_to(session_dir)),
            },
        )
    except Exception as e:
        logger.exception("File upload failed")
        return JSONResponse(status_code=500, content={"success": False, "message": f"Upload failed: {e!s}"})


@app.get("/download/{file_path:path}", summary="Download a file from the session directory")
async def download_file(
    file_path: str,
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    从会话目录下载文件。
    file_path 是相对于会话目录的路径。
    """
    full_path = FileService.get_file_path(user_id, thread_id, file_path)

    if full_path is None:
        raise HTTPException(status_code=404, detail="File not found or access denied")

    return FileResponse(path=str(full_path), media_type="application/octet-stream", filename=Path(file_path).name)


# ==================== 代码执行 ====================


@app.post("/execute", summary="Execute a shell command", response_model=ExecuteResponse)
async def execute_command(
    request: ExecuteRequest,
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    在会话目录中执行 Shell 命令。
    命令的工作目录自动设置为会话目录。
    """
    try:
        session_dir = ensure_session_dir(user_id, thread_id)

        # 使用 shell=True 以支持管道和重定向
        process = subprocess.run(
            request.command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(session_dir),
            timeout=60,
        )

        return ExecuteResponse(stdout=process.stdout, stderr=process.stderr, exit_code=process.returncode)
    except subprocess.TimeoutExpired:
        return ExecuteResponse(stdout="", stderr="Command execution timeout (60s)", exit_code=124)
    except Exception as e:
        return ExecuteResponse(stdout="", stderr=f"Failed to execute command: {e!s}", exit_code=1)


@app.post("/execute_python", summary="Execute Python code")
async def execute_python(
    request: CodeRequest,
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    在沙盒中执行 Python 代码。
    代码可以访问 pandas、numpy 等数据分析库。
    生成的文件会保存到会话目录。
    """
    session_dir = ensure_session_dir(user_id, thread_id)

    # 获取执行前的文件列表
    files_before = set(f["name"] for f in list_files_in_dir(session_dir))

    # 捕获输出
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    # 准备执行环境
    exec_globals = {
        "__builtins__": __builtins__,
        "__name__": "__main__",
        "WORK_DIR": session_dir,
    }

    # 切换到会话目录
    original_cwd = os.getcwd()
    original_path = sys.path.copy()

    try:
        os.chdir(session_dir)
        sys.path.insert(0, str(session_dir))

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(request.code, exec_globals)

        # 获取新创建的文件
        files_after = set(f["name"] for f in list_files_in_dir(session_dir))
        files_created = list(files_after - files_before)

        return CodeExecutionResult(
            success=True,
            output=stdout_buffer.getvalue(),
            files_created=files_created,
        )

    except Exception as e:
        error_traceback = traceback.format_exc()
        return CodeExecutionResult(
            success=False,
            output=stdout_buffer.getvalue(),
            error=f"{e!s}\n\n{error_traceback}",
        )
    finally:
        os.chdir(original_cwd)
        sys.path = original_path


@app.post("/execute_sql", summary="Execute SQL query using DuckDB")
async def execute_sql(
    request: SqlRequest,
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    使用会话的 DuckDB 文件执行 SQL 查询。

    数据通过会话初始化时创建的 VIEWs 访问，AI 可以直接查询这些 VIEWs。
    """
    import duckdb

    session_dir = ensure_session_dir(user_id, thread_id)
    duckdb_path = session_dir / "session.duckdb"

    try:
        # 如果会话 DuckDB 文件不存在，创建一个空的
        if not duckdb_path.exists():
            logger.warning(f"Session DuckDB not found, creating empty: {duckdb_path}")

        # 打开会话的 DuckDB 文件
        conn = duckdb.connect(str(duckdb_path))

        # 设置扩展目录
        extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
        conn.execute(f"SET extension_directory='{extensions_dir}';")

        # 配置 S3 访问（用于读取会话目录中的临时文件）
        configure_s3_access(conn)

        # 切换工作目录以便相对路径访问本地文件
        original_cwd = os.getcwd()
        os.chdir(session_dir)

        try:
            # 先用 EXPLAIN 检查 SQL 语法（不实际执行）
            try:
                conn.execute(f"EXPLAIN {request.sql}")
            except Exception as explain_error:
                # 语法错误，直接返回错误信息
                error_msg = str(explain_error)
                logger.warning(f"SQL syntax check failed: {error_msg}")
                return {"success": False, "error": error_msg}

            # 语法检查通过，执行实际查询
            result = conn.execute(request.sql)
            columns = [desc[0] for desc in result.description] if result.description else []

            # 使用 fetchmany 限制内存使用，避免大结果集导致 OOM
            max_rows = request.max_rows
            rows = result.fetchmany(max_rows + 1)  # 多取一行用于检测是否有更多数据
            has_more = len(rows) > max_rows
            if has_more:
                rows = rows[:max_rows]  # 截断到限制行数
                logger.warning(f"SQL result truncated to {max_rows} rows (has more data)")

            # 自动保存结果到 parquet 文件（供后续工具使用）
            result_file = None
            if rows and columns:
                import pandas as pd

                try:
                    df = pd.DataFrame(rows, columns=columns)
                    result_file = generate_unique_filename(session_dir, "sql_result_", ".parquet")
                    df.to_parquet(session_dir / result_file, index=False)
                    logger.info(f"SQL result saved to {result_file}")
                except Exception as e:
                    logger.warning(f"Failed to save SQL result: {e}")

            return {
                "success": True,
                "columns": columns,
                "rows": [list(row) for row in rows],
                "row_count": len(rows),
                "result_file": result_file,  # 结果文件路径
                "truncated": has_more,  # 是否被截断
                "max_rows": max_rows,  # 最大行数限制
            }
        finally:
            os.chdir(original_cwd)
            conn.close()

    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.exception("SQL execution failed")
        return {"success": False, "error": f"{e!s}\n\n{error_traceback}"}


# ==================== 数据分析 ====================


@app.post("/quick_analysis", summary="Quick data analysis")
async def quick_analysis(
    request: QuickAnalysisRequest,
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    快速分析数据，支持两种模式：

    1. 分析会话文件：指定 file_name 参数
    2. 分析数据源 VIEW：指定 view_names 或留空分析所有 VIEW
    """
    import duckdb

    session_dir = get_session_dir(user_id, thread_id)

    # ===== 模式 1：分析会话文件 =====
    if request.file_name:
        file_path = session_dir / request.file_name

        # 安全检查：防止路径穿越
        try:
            file_path.resolve().relative_to(session_dir.resolve())
        except ValueError:
            return {"success": False, "error": "Invalid file path: path traversal detected"}

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {request.file_name}"}

        conn = None
        try:
            conn = duckdb.connect(":memory:")
            extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
            conn.execute(f"SET extension_directory='{extensions_dir}';")

            # 根据文件类型选择读取方式
            file_ext = file_path.suffix.lower()
            original_cwd = os.getcwd()
            os.chdir(session_dir)

            try:
                if file_ext == ".parquet":
                    conn.execute(f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM '{request.file_name}'")
                elif file_ext == ".csv":
                    conn.execute(
                        f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM read_csv_auto('{request.file_name}', header=True)"
                    )
                elif file_ext == ".json":
                    conn.execute(
                        f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM read_json_auto('{request.file_name}')"
                    )
                else:
                    return {"success": False, "error": f"Unsupported file type: {file_ext}"}

                analysis = analyze_data_with_duckdb(conn, "data_preview")
                analysis["file_name"] = request.file_name

                return {"success": True, "analysis": analysis}
            finally:
                os.chdir(original_cwd)

        except Exception as e:
            logger.exception(f"Failed to analyze file {request.file_name}")
            return {"success": False, "error": str(e)}
        finally:
            if conn:
                conn.close()

    # ===== 模式 2：分析数据源 VIEW =====
    duckdb_path = session_dir / "session.duckdb"

    if not duckdb_path.exists():
        return {
            "success": False,
            "error": "Session DuckDB not initialized. Please create a session with data source first.",
        }

    conn = None
    try:
        conn = duckdb.connect(str(duckdb_path), read_only=True)

        # 设置扩展目录
        extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
        conn.execute(f"SET extension_directory='{extensions_dir}';")

        # 配置 S3 访问（VIEW 可能引用 S3 URL）
        configure_s3_access(conn)

        # 获取要分析的 VIEW 列表
        if request.view_names:
            view_names = request.view_names
        else:
            # 查询所有 VIEW
            views_result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
            ).fetchall()
            view_names = [row[0] for row in views_result]

        if not view_names:
            return {
                "success": True,
                "analysis": {
                    "views": [],
                    "message": "No VIEWs found in session DuckDB",
                },
            }

        # 分析每个 VIEW
        views_analysis = []
        for view_name in view_names:
            try:
                analysis = analyze_data_with_duckdb(conn, f'"{view_name}"')
                analysis["view_name"] = view_name
                views_analysis.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze view {view_name}: {e}")
                views_analysis.append(
                    {
                        "view_name": view_name,
                        "error": str(e),
                    }
                )

        # 如果只有一个 VIEW，简化返回结构
        if len(views_analysis) == 1:
            result_analysis = views_analysis[0]
        else:
            result_analysis = {
                "view_count": len(views_analysis),
                "views": views_analysis,
            }

        return {"success": True, "analysis": result_analysis}

    except Exception as e:
        logger.exception("Quick analysis failed")
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()


# ==================== 图表生成 ====================


@app.post("/generate_chart", summary="Generate Plotly chart")
async def generate_chart(
    request: ChartRequest,
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
):
    """
    执行 Python 代码生成 Plotly 图表。

    代码应该使用 plotly 库创建图表，并将 figure 对象赋值给 `fig` 变量。
    示例代码：
    ```python
    import plotly.express as px
    import pandas as pd

    df = pd.DataFrame({'x': [1,2,3], 'y': [4,5,6]})
    fig = px.bar(df, x='x', y='y', title='示例图表')
    ```
    """
    session_dir = ensure_session_dir(user_id, thread_id)

    # 捕获输出
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    # 准备执行环境
    exec_globals = {
        "__builtins__": __builtins__,
        "__name__": "__main__",
        "WORK_DIR": session_dir,
    }

    # 切换到会话目录
    original_cwd = os.getcwd()
    original_path = sys.path.copy()

    try:
        os.chdir(session_dir)
        sys.path.insert(0, str(session_dir))

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(request.code, exec_globals)

        # 检查是否创建了 fig 变量
        fig = exec_globals.get("fig")
        if fig is None:
            return {
                "success": False,
                "error": "代码执行成功，但未找到 'fig' 变量。请确保代码创建了名为 'fig' 的 Plotly figure 对象。",
                "output": stdout_buffer.getvalue(),
            }

        # 同时保存为 JSON 以便前端渲染
        chart_json = fig.to_json()

        return {
            "success": True,
            "chart_json": chart_json,
            "output": stdout_buffer.getvalue(),
        }

    except Exception as e:
        error_traceback = traceback.format_exc()
        return {
            "success": False,
            "output": stdout_buffer.getvalue(),
            "error": f"{e!s}\n\n{error_traceback}",
        }
    finally:
        os.chdir(original_cwd)
        sys.path = original_path
