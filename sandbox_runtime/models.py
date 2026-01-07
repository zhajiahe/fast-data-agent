"""
沙箱运行时 - Pydantic 模型定义

包含所有请求/响应模型
"""

from pydantic import BaseModel, Field


# ==================== 基础请求/响应模型 ====================


class ExecuteRequest(BaseModel):
    """Shell 命令执行请求"""

    command: str


class ExecuteResponse(BaseModel):
    """Shell 命令执行响应"""

    stdout: str
    stderr: str
    exit_code: int


class CodeRequest(BaseModel):
    """Python 代码执行请求"""

    code: str


class SqlRequest(BaseModel):
    """SQL 执行请求"""

    sql: str
    max_rows: int = Field(default=10000, ge=1, le=100000, description="结果集最大行数限制")


class ChartRequest(BaseModel):
    """图表生成请求"""

    code: str


class CodeExecutionResult(BaseModel):
    """代码执行结果"""

    success: bool
    output: str
    error: str | None = None
    files_created: list[str] = []


# ==================== 数据分析模型 ====================


class QuickAnalysisRequest(BaseModel):
    """快速分析请求模型"""

    # 要分析的 VIEW 名称列表，为空则分析所有 VIEW
    view_names: list[str] | None = None
    # 要分析的会话文件名（如 'sql_result_abcd.parquet'）
    file_name: str | None = None


# ==================== 会话初始化模型 ====================


class RawDataConfig(BaseModel):
    """数据对象配置"""

    id: str
    name: str
    raw_type: str  # "file" 或 "database_table"

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
    schema_name: str | None = None
    table_name: str | None = None
    custom_sql: str | None = None


class InitSessionRequest(BaseModel):
    """会话初始化请求 - 简化版"""

    raw_data_list: list[RawDataConfig] = Field(default_factory=list)
