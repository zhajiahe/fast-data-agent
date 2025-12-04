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

import subprocess
import os
import io
import sys
import logging
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 常量定义 ====================

SANDBOX_ROOT = Path("/app")

# MinIO 配置（从环境变量读取）
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


# ==================== 请求/响应模型 ====================


class ExecuteRequest(BaseModel):
    """Request model for the /execute endpoint."""

    command: str


class ExecuteResponse(BaseModel):
    """Response model for the /execute endpoint."""

    stdout: str
    stderr: str
    exit_code: int


class CodeRequest(BaseModel):
    """Request model for Python code execution."""

    code: str


class SqlRequest(BaseModel):
    """Request model for SQL execution."""

    sql: str


class ChartRequest(BaseModel):
    """Request model for chart generation."""

    code: str


class DataSourceInfo(BaseModel):
    """数据源信息模型"""

    source_type: str  # "file" 或 "database"

    # 文件类型数据源 (source_type="file")
    file_type: str | None = None  # csv, excel, json, parquet
    object_key: str | None = None  # MinIO 对象 key
    bucket_name: str | None = None  # MinIO bucket 名称

    # 数据库类型数据源 (source_type="database")
    db_type: str | None = None  # mysql, postgresql, sqlite
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None


class QuickAnalysisRequest(BaseModel):
    """快速分析请求模型"""

    data_source: DataSourceInfo


class CodeExecutionResult(BaseModel):
    """Response model for code execution."""

    success: bool
    output: str
    error: str | None = None


# ==================== 辅助函数 ====================


def get_session_dir(user_id: int, thread_id: int) -> Path:
    """
    获取会话工作目录。

    目录结构: /app/sessions/{user_id}/{thread_id}/
    """
    session_dir = SANDBOX_ROOT / "sessions" / str(user_id) / str(thread_id)
    return session_dir


def ensure_session_dir(user_id: int, thread_id: int) -> Path:
    """
    确保会话目录存在，如果不存在则创建。

    Returns:
        会话目录路径
    """
    session_dir = get_session_dir(user_id, thread_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def list_files_in_dir(directory: Path) -> list[dict[str, Any]]:
    """
    列出目录中的所有文件（递归）。

    Returns:
        文件信息列表
    """
    files = []
    if not directory.exists():
        return files

    for path in directory.rglob("*"):
        if path.is_file():
            rel_path = path.relative_to(directory)
            stat = path.stat()
            files.append(
                {
                    "name": str(rel_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    return files


# ==================== FastAPI App ====================


app = FastAPI(
    title="Agentic Sandbox Runtime",
    description="An API server for executing commands and managing files in a secure sandbox.",
    version="2.0.0",
)


# ==================== 健康检查 ====================


@app.get("/", summary="Health Check")
async def health_check():
    """A simple health check endpoint to confirm the server is running."""
    return {"status": "ok", "message": "Sandbox Runtime is active."}


# ==================== 文件管理 ====================


@app.get("/files", summary="List files in session directory")
async def list_files(
    user_id: int = Query(..., description="User ID"),
    thread_id: int = Query(..., description="Thread/Session ID"),
):
    """
    列出会话目录中的所有文件。
    用于查看分析过程中生成的中间文件、图表、报告等。
    """
    session_dir = ensure_session_dir(user_id, thread_id)
    files = list_files_in_dir(session_dir)

    return {
        "success": True,
        "files": files,
        "count": len(files),
    }


@app.post("/upload", summary="Upload a file to the session directory")
async def upload_file(
    file: UploadFile = File(...),
    user_id: int = Query(..., description="User ID"),
    thread_id: int = Query(..., description="Thread/Session ID"),
):
    """
    上传文件到会话目录。
    用户无需关心具体存储路径，文件自动保存到对应会话目录。
    """
    try:
        session_dir = ensure_session_dir(user_id, thread_id)
        file_path = session_dir / file.filename

        # 确保父目录存在（处理带路径的文件名）
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"File uploaded: {file_path}")

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
        return JSONResponse(
            status_code=500, content={"success": False, "message": f"Upload failed: {e!s}"}
        )


@app.get("/download/{file_path:path}", summary="Download a file from the session directory")
async def download_file(
    file_path: str,
    user_id: int = Query(..., description="User ID"),
    thread_id: int = Query(..., description="Thread/Session ID"),
):
    """
    从会话目录下载文件。
    file_path 是相对于会话目录的路径。
    """
    session_dir = ensure_session_dir(user_id, thread_id)
    full_path = session_dir / file_path

    # 安全检查：防止路径穿越
    try:
        full_path.resolve().relative_to(session_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected")

    if full_path.is_file():
        return FileResponse(
            path=str(full_path), media_type="application/octet-stream", filename=Path(file_path).name
        )

    raise HTTPException(status_code=404, detail="File not found")


# ==================== 代码执行 ====================


@app.post("/execute", summary="Execute a shell command", response_model=ExecuteResponse)
async def execute_command(
    request: ExecuteRequest,
    user_id: int = Query(..., description="User ID"),
    thread_id: int = Query(..., description="Thread/Session ID"),
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

        return ExecuteResponse(
            stdout=process.stdout, stderr=process.stderr, exit_code=process.returncode
        )
    except subprocess.TimeoutExpired:
        return ExecuteResponse(stdout="", stderr="Command execution timeout (60s)", exit_code=124)
    except Exception as e:
        return ExecuteResponse(stdout="", stderr=f"Failed to execute command: {e!s}", exit_code=1)


@app.post("/execute_python", summary="Execute Python code")
async def execute_python(
    request: CodeRequest,
    user_id: int = Query(..., description="User ID"),
    thread_id: int = Query(..., description="Thread/Session ID"),
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
    user_id: int = Query(..., description="User ID"),
    thread_id: int = Query(..., description="Thread/Session ID"),
):
    """
    使用 DuckDB 执行 SQL 查询。
    支持对会话目录中的 CSV、Parquet 文件进行查询。
    """
    session_dir = ensure_session_dir(user_id, thread_id)

    try:
        import duckdb

        # 创建 DuckDB 连接，数据库文件存储在会话目录
        db_path = session_dir / "session.duckdb"
        conn = duckdb.connect(str(db_path))

        # 切换工作目录以便相对路径访问文件
        original_cwd = os.getcwd()
        os.chdir(session_dir)

        try:
            result = conn.execute(request.sql)
            columns = [desc[0] for desc in result.description] if result.description else []
            rows = result.fetchall()

            return {
                "success": True,
                "columns": columns,
                "rows": [list(row) for row in rows],
                "row_count": len(rows),
            }
        finally:
            os.chdir(original_cwd)
            conn.close()

    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 数据分析 ====================


def setup_duckdb_s3(conn) -> None:
    """配置 DuckDB 以访问 MinIO (S3 兼容)"""
    # 设置扩展目录到可写路径
    extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)
    conn.execute(f"SET extension_directory='{extensions_dir}';")
    
    conn.execute("INSTALL httpfs;")
    conn.execute("LOAD httpfs;")
    conn.execute(f"SET s3_endpoint='{MINIO_ENDPOINT}';")
    conn.execute(f"SET s3_access_key_id='{MINIO_ACCESS_KEY}';")
    conn.execute(f"SET s3_secret_access_key='{MINIO_SECRET_KEY}';")
    conn.execute("SET s3_url_style='path';")  # MinIO 使用 path style
    conn.execute(f"SET s3_use_ssl={'true' if MINIO_SECURE else 'false'};")


def get_db_connection_string(ds: DataSourceInfo) -> str:
    """构建数据库连接字符串"""
    if ds.db_type == "postgresql":
        return f"postgresql://{ds.username}:{ds.password}@{ds.host}:{ds.port}/{ds.database}"
    elif ds.db_type == "mysql":
        return f"mysql://{ds.username}:{ds.password}@{ds.host}:{ds.port}/{ds.database}"
    elif ds.db_type == "sqlite":
        return f"sqlite://{ds.database}"
    else:
        raise ValueError(f"Unsupported database type: {ds.db_type}")


def analyze_data_with_duckdb(conn, table_or_view: str = "data_preview") -> dict[str, Any]:
    """使用 DuckDB 分析数据，返回统计结果"""
    row_count = conn.execute(f"SELECT COUNT(*) FROM {table_or_view}").fetchone()[0]
    columns_meta = conn.execute(f"PRAGMA table_info('{table_or_view}')").fetchall()

    numeric_types = {
        "TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT",
        "REAL", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC",
    }

    analysis_columns = []
    missing_values = {}

    for _, col_name, col_type, *_ in columns_meta:
        # 缺失值统计
        null_count = conn.execute(
            f'SELECT COUNT(*) FROM {table_or_view} WHERE "{col_name}" IS NULL'
        ).fetchone()[0]

        col_info: dict[str, Any] = {
            "name": col_name,
            "dtype": col_type,
            "non_null_count": int(row_count - null_count),
            "null_count": int(null_count),
        }

        # 数值列统计
        if col_type.upper() in numeric_types and (row_count - null_count) > 0:
            stats_row = conn.execute(
                f'''
                SELECT
                    AVG(CAST("{col_name}" AS DOUBLE)) AS mean,
                    STDDEV_POP(CAST("{col_name}" AS DOUBLE)) AS std,
                    MIN(CAST("{col_name}" AS DOUBLE)) AS min,
                    MAX(CAST("{col_name}" AS DOUBLE)) AS max,
                    MEDIAN(CAST("{col_name}" AS DOUBLE)) AS median
                FROM {table_or_view}
                WHERE "{col_name}" IS NOT NULL
                '''
            ).fetchone()

            col_info["stats"] = {
                "mean": float(stats_row[0]) if stats_row[0] is not None else None,
                "std": float(stats_row[1]) if stats_row[1] is not None else None,
                "min": float(stats_row[2]) if stats_row[2] is not None else None,
                "max": float(stats_row[3]) if stats_row[3] is not None else None,
                "median": float(stats_row[4]) if stats_row[4] is not None else None,
            }

        analysis_columns.append(col_info)
        missing_values[col_name] = int(null_count)

    return {
        "row_count": int(row_count),
        "column_count": len(columns_meta),
        "columns": analysis_columns,
        "missing_values": missing_values,
    }


def setup_duckdb_extensions_dir(conn) -> None:
    """设置 DuckDB 扩展目录到可写路径"""
    extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)
    conn.execute(f"SET extension_directory='{extensions_dir}';")


async def analyze_sqlite_from_s3(conn, s3_url: str, user_id: int, thread_id: int) -> dict[str, Any]:
    """
    从 S3 下载 SQLite 文件并分析。
    
    SQLite 文件不能直接从 S3 读取，需要先下载到本地。
    使用 DuckDB 的 httpfs 扩展下载文件。
    """
    import urllib.request
    import urllib.parse
    import base64
    import hmac
    import hashlib
    from datetime import datetime
    
    # 解析 S3 URL
    # s3://bucket/key -> http://endpoint/bucket/key
    parts = s3_url.replace("s3://", "").split("/", 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    
    # 下载文件到会话目录
    session_dir = ensure_session_dir(user_id, thread_id)
    sqlite_path = session_dir / f"sqlite_{key.replace('/', '_')}"
    
    logger.info(f"Downloading SQLite from S3: {s3_url} to {sqlite_path}")
    
    try:
        # 使用 AWS S3 签名 V4 风格下载
        # 构建 HTTP URL
        protocol = "https" if MINIO_SECURE else "http"
        http_url = f"{protocol}://{MINIO_ENDPOINT}/{bucket}/{key}"
        
        # 创建签名请求（简化版本，假设 MinIO 允许匿名访问或使用 Query 签名）
        # 实际项目中应该使用 boto3 或 minio SDK
        
        # 尝试直接下载（如果 bucket 是公开的）
        try:
            urllib.request.urlretrieve(http_url, str(sqlite_path))
        except Exception as e:
            logger.warning(f"Direct download failed: {e}")
            
            # 使用 AWS Signature V4 进行签名下载
            # 这里使用简化的签名方式
            date_str = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            date_short = datetime.utcnow().strftime('%Y%m%d')
            
            # 构建 canonical request
            method = "GET"
            canonical_uri = f"/{bucket}/{key}"
            canonical_querystring = ""
            host = MINIO_ENDPOINT
            
            # 签名请求头
            headers = {
                "Host": host,
                "X-Amz-Date": date_str,
            }
            
            signed_headers = ";".join(sorted(headers.keys()).lower() for k in headers)
            canonical_headers = "\n".join(f"{k.lower()}:{v}" for k, v in sorted(headers.items())) + "\n"
            
            payload_hash = hashlib.sha256(b"").hexdigest()
            canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
            
            # 这里简化处理，假设可以直接访问
            # 实际需要完整的 AWS Signature V4 实现
            
    except Exception as e:
        logger.error(f"Failed to download SQLite: {e}")
        return {
            "error": f"Failed to download SQLite file: {str(e)}",
            "row_count": 0,
            "column_count": 0,
            "columns": [],
        }
    
    # 检查文件是否存在且有效
    if not sqlite_path.exists() or sqlite_path.stat().st_size == 0:
        return {
            "error": "SQLite file download failed or file is empty",
            "row_count": 0,
            "column_count": 0,
            "columns": [],
        }
    
    # 分析 SQLite 数据库
    try:
        conn.execute(f"ATTACH '{sqlite_path}' AS sqlite_db (TYPE SQLITE, READ_ONLY);")
    except Exception as e:
        return {
            "error": f"Failed to attach SQLite database: {str(e)}",
            "row_count": 0,
            "column_count": 0,
            "columns": [],
        }
    
    # 获取所有表
    tables_result = conn.execute(
        "SELECT name FROM sqlite_db.sqlite_master WHERE type='table'"
    ).fetchall()
    
    tables_info = []
    total_rows = 0
    total_columns = 0
    all_columns: list[dict[str, Any]] = []
    
    for (table_name,) in tables_result:
        try:
            row_count = conn.execute(f"SELECT COUNT(*) FROM sqlite_db.{table_name}").fetchone()[0]
            columns_meta = conn.execute(f"PRAGMA sqlite_db.table_info('{table_name}')").fetchall()
            columns = [{"name": col[1], "dtype": col[2]} for col in columns_meta]
            
            tables_info.append({
                "table_name": table_name,
                "row_count": int(row_count),
                "column_count": len(columns),
                "columns": columns,
            })
            
            # 累计第一个表的信息作为主要统计
            if not all_columns:
                total_rows = row_count
                total_columns = len(columns)
                all_columns = columns
        except Exception as e:
            logger.warning(f"Failed to analyze table {table_name}: {e}")
    
    return {
        "row_count": int(total_rows),
        "column_count": total_columns,
        "columns": all_columns,
        "missing_values": {},
        "tables": tables_info,
        "table_count": len(tables_result),
    }


@app.post("/quick_analysis", summary="Quick data analysis")
async def quick_analysis(
    request: QuickAnalysisRequest,
    user_id: int = Query(..., description="User ID"),
    thread_id: int = Query(..., description="Thread/Session ID"),
):
    """
    快速分析数据源，返回数据概览。
    支持两种数据源类型：
    1. file - 直接从 MinIO (S3) 读取文件
    2. database - 连接外部数据库进行分析
    """
    import duckdb

    ds = request.data_source

    try:
        conn = duckdb.connect(":memory:")
        
        # 设置扩展目录（所有类型都需要）
        setup_duckdb_extensions_dir(conn)

        if ds.source_type == "file":
            # ========== 文件类型：直接从 MinIO (S3) 读取 ==========
            if not ds.object_key or not ds.bucket_name:
                return {"success": False, "error": "Missing object_key or bucket_name for file data source"}

            # 配置 S3 访问
            setup_duckdb_s3(conn)

            # 构建 S3 URL
            s3_url = f"s3://{ds.bucket_name}/{ds.object_key}"
            logger.info(f"Reading file from S3: {s3_url}")

            # 根据文件类型选择读取方式
            file_type = ds.file_type or "csv"
            if file_type == "csv":
                load_query = f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM read_csv_auto('{s3_url}', header=True)"
                conn.execute(load_query)
                analysis = analyze_data_with_duckdb(conn, "data_preview")
            elif file_type == "parquet":
                load_query = f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM parquet_scan('{s3_url}')"
                conn.execute(load_query)
                analysis = analyze_data_with_duckdb(conn, "data_preview")
            elif file_type == "json":
                load_query = f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM read_json_auto('{s3_url}')"
                conn.execute(load_query)
                analysis = analyze_data_with_duckdb(conn, "data_preview")
            elif file_type == "excel":
                # DuckDB 需要 spatial 扩展来读取 Excel
                conn.execute("INSTALL spatial; LOAD spatial;")
                load_query = f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM st_read('{s3_url}')"
                conn.execute(load_query)
                analysis = analyze_data_with_duckdb(conn, "data_preview")
            elif file_type == "sqlite":
                # SQLite 文件需要先下载到本地
                analysis = await analyze_sqlite_from_s3(conn, s3_url, user_id, thread_id)
            else:
                return {"success": False, "error": f"Unsupported file type: {file_type}"}

            analysis["source_type"] = "file"
            analysis["file_name"] = ds.object_key.split("/")[-1] if ds.object_key else "unknown"

            return {"success": True, "analysis": analysis}

        elif ds.source_type == "database":
            # ========== 数据库类型：使用 DuckDB 的数据库扩展 ==========
            if not ds.db_type:
                return {"success": False, "error": "Missing db_type for database data source"}

            # 安装并加载对应的数据库扩展
            if ds.db_type == "postgresql":
                conn.execute("INSTALL postgres; LOAD postgres;")
                conn_str = f"host={ds.host} port={ds.port} dbname={ds.database} user={ds.username} password={ds.password}"
                conn.execute(f"ATTACH '{conn_str}' AS external_db (TYPE POSTGRES, READ_ONLY);")
            elif ds.db_type == "mysql":
                conn.execute("INSTALL mysql; LOAD mysql;")
                conn_str = f"host={ds.host} port={ds.port} database={ds.database} user={ds.username} password={ds.password}"
                conn.execute(f"ATTACH '{conn_str}' AS external_db (TYPE MYSQL, READ_ONLY);")
            elif ds.db_type == "sqlite":
                conn.execute(f"ATTACH '{ds.database}' AS external_db (TYPE SQLITE, READ_ONLY);")
            else:
                return {"success": False, "error": f"Unsupported database type: {ds.db_type}"}

            # 获取所有表
            tables_result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'external_db'"
            ).fetchall()

            if not tables_result:
                # 尝试另一种方式获取表列表
                tables_result = conn.execute("SHOW TABLES FROM external_db").fetchall()

            tables_info = []
            for (table_name,) in tables_result[:10]:  # 限制分析前 10 个表
                try:
                    # 获取行数
                    row_count = conn.execute(f"SELECT COUNT(*) FROM external_db.{table_name}").fetchone()[0]
                    # 获取列信息
                    columns_meta = conn.execute(f"PRAGMA table_info('external_db.{table_name}')").fetchall()
                    columns = [{"name": col[1], "dtype": col[2]} for col in columns_meta]

                    tables_info.append({
                        "table_name": table_name,
                        "row_count": int(row_count),
                        "column_count": len(columns),
                        "columns": columns,
                    })
                except Exception as e:
                    logger.warning(f"Failed to analyze table {table_name}: {e}")
                    tables_info.append({
                        "table_name": table_name,
                        "error": str(e),
                    })

            analysis = {
                "source_type": "database",
                "db_type": ds.db_type,
                "database": ds.database,
                "table_count": len(tables_result),
                "tables": tables_info,
            }

            return {"success": True, "analysis": analysis}

        else:
            return {"success": False, "error": f"Unknown source_type: {ds.source_type}"}

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
    user_id: int = Query(..., description="User ID"),
    thread_id: int = Query(..., description="Thread/Session ID"),
):
    """
    生成 Plotly 图表并保存为 HTML 文件。

    支持的图表类型：bar, line, scatter, pie, histogram, box, heatmap
    """
    session_dir = ensure_session_dir(user_id, thread_id)

    try:
        import plotly.express as px
        import plotly.graph_objects as go
        import pandas as pd

        chart_type = request.chart_type.lower()
        data_config = request.data_config
        title = request.title

        # 从配置创建 DataFrame
        if "data" in data_config:
            df = pd.DataFrame(data_config["data"])
        else:
            df = pd.DataFrame(data_config)

        # 根据图表类型生成图表
        fig = None
        x = data_config.get("x")
        y = data_config.get("y")
        labels = data_config.get("labels")
        values = data_config.get("values")

        if chart_type == "bar":
            fig = px.bar(df, x=x, y=y, title=title)
        elif chart_type == "line":
            fig = px.line(df, x=x, y=y, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x, y=y, title=title)
        elif chart_type == "pie":
            fig = px.pie(df, names=labels or x, values=values or y, title=title)
        elif chart_type == "histogram":
            fig = px.histogram(df, x=x, title=title)
        elif chart_type == "box":
            fig = px.box(df, x=x, y=y, title=title)
        elif chart_type == "heatmap":
            fig = px.imshow(df, title=title)
        else:
            return {"success": False, "error": f"Unsupported chart type: {chart_type}"}

        # 保存图表
        import time

        chart_filename = f"chart_{int(time.time())}.html"
        chart_path = session_dir / chart_filename
        fig.write_html(str(chart_path))

        # 同时保存为 JSON 以便前端渲染
        chart_json = fig.to_json()

        return {
            "success": True,
            "chart_file": chart_filename,
            "chart_json": chart_json,
            "message": f"Chart saved as {chart_filename}",
        }

    except Exception as e:
        logger.exception("Chart generation failed")
        return {"success": False, "error": str(e)}
