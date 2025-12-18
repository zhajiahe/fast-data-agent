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
from pydantic import BaseModel, Field

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


# ==================== DuckDB 连接管理器 ====================


class DuckDBConnectionManager:
    """
    DuckDB 连接管理器
    - 启动时预加载 httpfs 扩展
    - 提供配置好 S3 访问的连接
    """

    def __init__(self):
        self._extensions_loaded = False
        self._extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
        self._extensions_dir.mkdir(parents=True, exist_ok=True)

    def preload_extensions(self) -> None:
        """预加载 DuckDB 扩展（启动时调用）"""
        if self._extensions_loaded:
            return

        import duckdb

        logger.info("预加载 DuckDB 扩展...")
        try:
            conn = duckdb.connect(":memory:")
            conn.execute(f"SET extension_directory='{self._extensions_dir}';")
            # 预安装常用扩展
            conn.execute("INSTALL httpfs;")
            conn.close()
            self._extensions_loaded = True
            logger.info("DuckDB 扩展预加载完成")
        except Exception as e:
            logger.warning(f"预加载 DuckDB 扩展失败: {e}")

    def get_connection(self, with_s3: bool = False):
        """
        获取配置好的 DuckDB 连接

        Args:
            with_s3: 是否配置 S3 访问

        Returns:
            配置好的 DuckDB 连接
        """
        import duckdb

        conn = duckdb.connect(":memory:")
        conn.execute(f"SET extension_directory='{self._extensions_dir}';")

        if with_s3:
            configure_s3_access(conn)

        return conn


# 全局连接管理器实例
duckdb_manager = DuckDBConnectionManager()


def configure_s3_access(conn) -> None:
    """
    配置 DuckDB 连接的 S3 (MinIO) 访问。
    
    在已有连接上配置 httpfs 扩展和 S3 认证信息。
    适用于 session.duckdb 持久连接或需要访问 S3 的场景。
    
    Args:
        conn: DuckDB 连接实例
    """
    conn.execute("LOAD httpfs;")
    conn.execute(f"SET s3_endpoint='{MINIO_ENDPOINT}';")
    conn.execute(f"SET s3_access_key_id='{MINIO_ACCESS_KEY}';")
    conn.execute(f"SET s3_secret_access_key='{MINIO_SECRET_KEY}';")
    conn.execute("SET s3_url_style='path';")
    conn.execute(f"SET s3_use_ssl={'true' if MINIO_SECURE else 'false'};")


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
    max_rows: int = Field(default=10000, ge=1, le=100000, description="结果集最大行数限制")


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
    db_type: str | None = None  # mysql, postgresql
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None


class QuickAnalysisRequest(BaseModel):
    """快速分析请求模型（新版：支持 VIEW 和文件）"""

    # 要分析的 VIEW 名称列表，为空则分析所有 VIEW
    view_names: list[str] | None = None
    # 要分析的会话文件名（如 'sql_result_abcd.parquet'）
    file_name: str | None = None



class CodeExecutionResult(BaseModel):
    """Response model for code execution."""

    success: bool
    output: str
    error: str | None = None
    files_created: list[str] = []  # 执行过程中创建的文件


# ==================== 会话初始化模型 ====================


class RawDataConfig(BaseModel):
    """数据对象配置"""

    id: str  # UUID 字符串
    name: str  # 用于创建 VIEW 的名称
    raw_type: str  # "database_table" 或 "file"

    # 数据库表类型配置
    db_type: str | None = None  # mysql, postgresql
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    password: str | None = None
    schema_name: str | None = None
    table_name: str | None = None
    custom_sql: str | None = None

    # 文件类型配置
    file_type: str | None = None  # csv, excel, json, parquet
    object_key: str | None = None
    bucket_name: str | None = None


class FieldMapping(BaseModel):
    """单个 RawData 的字段映射配置"""

    raw_data_id: str  # UUID 字符串
    raw_data_name: str
    # 字段映射：{target_field: source_field}
    mappings: dict[str, str]


class DataSourceConfig(BaseModel):
    """数据源配置"""

    id: str  # UUID 字符串
    name: str
    raw_data_list: list[RawDataConfig]
    # 目标字段列表（统一后的逻辑字段）
    target_fields: list[dict] | None = None  # [{name, data_type, description}]
    # 字段映射配置列表
    raw_mappings: list[FieldMapping] | None = None


class InitSessionRequest(BaseModel):
    """初始化会话请求"""

    data_source: DataSourceConfig | None = None


# ==================== 辅助函数 ====================


def get_session_dir(user_id: str, thread_id: str) -> Path:
    """
    获取会话工作目录。

    目录结构: /app/sessions/{user_id}/{thread_id}/
    """
    session_dir = SANDBOX_ROOT / "sessions" / str(user_id) / str(thread_id)
    return session_dir


def ensure_session_dir(user_id: str, thread_id: str) -> Path:
    """
    确保会话目录存在，如果不存在则创建。

    Returns:
        会话目录路径
    """
    session_dir = get_session_dir(user_id, thread_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def generate_unique_filename(directory: Path, prefix: str, ext: str) -> str:
    """
    生成唯一的文件名（4 个随机字母）。
    
    Args:
        directory: 目标目录
        prefix: 文件名前缀（如 "sql_result_"）
        ext: 文件扩展名（如 ".parquet"）
    
    Returns:
        唯一的文件名（如 "sql_result_abcd.parquet"）
    """
    import random
    import string
    
    for _ in range(100):  # 最多尝试 100 次
        suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
        filename = f"{prefix}{suffix}{ext}"
        if not (directory / filename).exists():
            return filename
    
    # 如果 100 次都冲突，使用时间戳兜底
    import time
    return f"{prefix}{int(time.time())}{ext}"


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


# ==================== 应用生命周期 ====================


from contextlib import asynccontextmanager


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

                views_info.append({
                    "name": view_name,
                    "columns": columns,
                    "column_count": len(columns),
                    "row_count": row_count,
                })
            except Exception as e:
                logger.warning(f"Failed to get info for view {view_name}: {e}")
                views_info.append({
                    "name": view_name,
                    "error": str(e),
                })

        conn.close()

        return {
            "success": True,
            "views": views_info,
            "view_count": len(views_info),
        }

    except Exception as e:
        logger.exception(f"Failed to list views: {e}")
        return {"success": False, "error": str(e), "views": []}


@app.post("/init_session", summary="Initialize session DuckDB with data source")
async def init_session(
    request: InitSessionRequest,
    user_id: str = Query(..., description="User ID (UUID string)"),
    thread_id: str = Query(..., description="Thread/Session ID (UUID string)"),
):
    """
    初始化会话的 DuckDB 文件。

    创建一个持久化的 DuckDB 文件，并根据数据源配置：
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

        # 如果没有数据源，只创建空的 DuckDB 文件
        if not request.data_source:
            conn.close()
            return {
                "success": True,
                "message": "Session DuckDB initialized (no data source)",
                "duckdb_path": str(duckdb_path),
                "views_created": [],
                "errors": [],
            }

        ds = request.data_source

        # 构建 RawData ID 到 name 的映射
        raw_id_to_name: dict[str, str] = {}

        # Step 1: 为每个 RawData 创建原始 VIEW
        for raw_data in ds.raw_data_list:
            try:
                view_name = raw_data.name  # 使用 RawData 名称作为 VIEW 名称
                raw_id_to_name[raw_data.id] = view_name

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
                            conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM {attach_name}.{schema}.{table}')

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
                            conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM {attach_name}.{table}')

                    views_created.append(view_name)

                elif raw_data.raw_type == "file":
                    # 文件类型：通过 S3/httpfs 创建 VIEW
                    configure_s3_access(conn)

                    s3_url = f"s3://{raw_data.bucket_name}/{raw_data.object_key}"

                    if raw_data.file_type == "csv":
                        conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM read_csv_auto(\'{s3_url}\', header=True)')
                    elif raw_data.file_type == "parquet":
                        conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM parquet_scan(\'{s3_url}\')')
                    elif raw_data.file_type == "json":
                        conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM read_json_auto(\'{s3_url}\')')
                    elif raw_data.file_type == "excel":
                        conn.execute("INSTALL spatial; LOAD spatial;")
                        conn.execute(f'CREATE OR REPLACE VIEW "{view_name}" AS SELECT * FROM st_read(\'{s3_url}\')')

                    views_created.append(view_name)

            except Exception as e:
                error_msg = f"Failed to create view for {raw_data.name}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # Step 2: 如果有字段映射，创建 DataSource 级别的统一 VIEW
        if ds.raw_mappings and ds.target_fields and views_created:
            try:
                ds_view_name = ds.name  # DataSource 名称作为统一 VIEW 名称

                # 获取目标字段名列表
                target_field_names = [f["name"] for f in ds.target_fields]

                # 为每个有映射的 RawData 生成 SELECT 语句
                select_parts: list[str] = []
                for mapping in ds.raw_mappings:
                    raw_view_name = raw_id_to_name.get(mapping.raw_data_id)
                    if not raw_view_name or raw_view_name not in views_created:
                        continue

                    # 构建字段选择列表：target_field AS source_field
                    field_selects: list[str] = []
                    for target_field in target_field_names:
                        source_field = mapping.mappings.get(target_field)
                        if source_field:
                            # 有映射：使用 source_field AS target_field
                            field_selects.append(f'"{source_field}" AS "{target_field}"')
                        else:
                            # 无映射：使用 NULL
                            field_selects.append(f'NULL AS "{target_field}"')

                    if field_selects:
                        select_sql = f'SELECT {", ".join(field_selects)} FROM "{raw_view_name}"'
                        select_parts.append(select_sql)

                if select_parts:
                    # 使用 UNION ALL 合并多个 RawData 的映射视图
                    union_sql = " UNION ALL ".join(select_parts)
                    conn.execute(f'CREATE OR REPLACE VIEW "{ds_view_name}" AS {union_sql}')
                    views_created.append(ds_view_name)
                    logger.info(f"Created DataSource unified VIEW: {ds_view_name}")

            except Exception as e:
                error_msg = f"Failed to create DataSource unified view: {str(e)}"
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
        import traceback

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
    import shutil

    session_dir = get_session_dir(user_id, thread_id)

    if not session_dir.exists():
        return {
            "success": True,
            "message": "Session directory does not exist, nothing to clean",
            "deleted_count": 0,
        }

    try:
        # 统计文件数量
        files = list_files_in_dir(session_dir)
        deleted_count = len(files)

        # 删除目录内容
        shutil.rmtree(session_dir)
        session_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Reset session: user_id={user_id}, thread_id={thread_id}, deleted={deleted_count} files")

        return {
            "success": True,
            "message": f"Session reset successfully",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        logger.exception(f"Failed to reset session: {e}")
        return {"success": False, "error": str(e)}


@app.post("/reset/user", summary="Reset all user sessions")
async def reset_user(
    user_id: str = Query(..., description="User ID"),
):
    """
    重置指定用户的所有会话文件。
    删除该用户目录下的所有文件。
    """
    import shutil

    user_dir = SANDBOX_ROOT / "sessions" / str(user_id)

    if not user_dir.exists():
        return {
            "success": True,
            "message": "User directory does not exist, nothing to clean",
            "deleted_count": 0,
            "session_count": 0,
        }

    try:
        # 统计会话和文件数量
        session_count = len([d for d in user_dir.iterdir() if d.is_dir()])
        file_count = 0
        for session_dir in user_dir.iterdir():
            if session_dir.is_dir():
                file_count += len(list_files_in_dir(session_dir))

        # 删除用户目录
        shutil.rmtree(user_dir)

        logger.info(f"Reset user: user_id={user_id}, deleted={file_count} files in {session_count} sessions")

        return {
            "success": True,
            "message": f"User data reset successfully",
            "deleted_count": file_count,
            "session_count": session_count,
        }
    except Exception as e:
        logger.exception(f"Failed to reset user: {e}")
        return {"success": False, "error": str(e)}


@app.post("/reset/all", summary="Reset all sandbox data")
async def reset_all():
    """
    重置所有沙盒数据。
    删除 sessions 目录下的所有文件。
    仅用于管理目的，谨慎使用。
    """
    import shutil

    sessions_dir = SANDBOX_ROOT / "sessions"

    if not sessions_dir.exists():
        return {
            "success": True,
            "message": "Sessions directory does not exist, nothing to clean",
            "deleted_count": 0,
            "user_count": 0,
        }

    try:
        # 统计用户和文件数量
        user_count = len([d for d in sessions_dir.iterdir() if d.is_dir()])
        file_count = 0
        for user_dir in sessions_dir.iterdir():
            if user_dir.is_dir():
                for session_dir in user_dir.iterdir():
                    if session_dir.is_dir():
                        file_count += len(list_files_in_dir(session_dir))

        # 删除整个 sessions 目录并重建
        shutil.rmtree(sessions_dir)
        sessions_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Reset all: deleted={file_count} files from {user_count} users")

        return {
            "success": True,
            "message": "All sandbox data reset successfully",
            "deleted_count": file_count,
            "user_count": user_count,
        }
    except Exception as e:
        logger.exception(f"Failed to reset all: {e}")
        return {"success": False, "error": str(e)}


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
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
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
    user_id: str = Query(..., description="User ID"),
    thread_id: str = Query(..., description="Thread/Session ID"),
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
        import traceback

        error_traceback = traceback.format_exc()
        logger.exception("SQL execution failed")
        return {"success": False, "error": f"{e!s}\n\n{error_traceback}"}


# ==================== 数据分析 ====================


def setup_duckdb_s3(conn) -> None:
    """
    配置 DuckDB 以访问 MinIO (S3 兼容)。
    
    包含 INSTALL httpfs（用于首次未预加载的场景）。
    如果扩展已预加载，使用 configure_s3_access() 即可。
    """
    # 设置扩展目录到可写路径
    extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)
    conn.execute(f"SET extension_directory='{extensions_dir}';")
    
    conn.execute("INSTALL httpfs;")
    configure_s3_access(conn)


def get_db_connection_string(ds: DataSourceInfo) -> str:
    """构建数据库连接字符串"""
    if ds.db_type == "postgresql":
        return f"postgresql://{ds.username}:{ds.password}@{ds.host}:{ds.port}/{ds.database}"
    elif ds.db_type == "mysql":
        return f"mysql://{ds.username}:{ds.password}@{ds.host}:{ds.port}/{ds.database}"
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
    import os

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
                    conn.execute(f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM read_csv_auto('{request.file_name}', header=True)")
                elif file_ext == ".json":
                    conn.execute(f"CREATE OR REPLACE TEMP VIEW data_preview AS SELECT * FROM read_json_auto('{request.file_name}')")
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
                views_analysis.append({
                    "view_name": view_name,
                    "error": str(e),
                })

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
