"""
沙箱运行时 - DuckDB 服务

包含 DuckDB 连接管理和数据分析功能
"""

import logging
from typing import Any

from sandbox_runtime.utils import (
    SANDBOX_ROOT,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
)

logger = logging.getLogger(__name__)


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


# ==================== S3 配置函数 ====================


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


def setup_duckdb_extensions_dir(conn) -> None:
    """设置 DuckDB 扩展目录到可写路径"""
    extensions_dir = SANDBOX_ROOT / "duckdb_extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)
    conn.execute(f"SET extension_directory='{extensions_dir}';")


def setup_duckdb_s3(conn) -> None:
    """
    配置 DuckDB 以访问 MinIO (S3 兼容)。

    包含 INSTALL httpfs（用于首次未预加载的场景）。
    如果扩展已预加载，使用 configure_s3_access() 即可。
    """
    setup_duckdb_extensions_dir(conn)
    conn.execute("INSTALL httpfs;")
    configure_s3_access(conn)


# ==================== 数据分析函数 ====================


def analyze_data_with_duckdb(conn, table_or_view: str = "data_preview") -> dict[str, Any]:
    """
    使用 DuckDB 分析数据，返回统计结果。

    Args:
        conn: DuckDB 连接
        table_or_view: 要分析的表或视图名称

    Returns:
        包含统计信息的字典
    """
    row_count = conn.execute(f"SELECT COUNT(*) FROM {table_or_view}").fetchone()[0]
    columns_meta = conn.execute(f"PRAGMA table_info('{table_or_view}')").fetchall()

    numeric_types = {
        "TINYINT",
        "SMALLINT",
        "INTEGER",
        "BIGINT",
        "HUGEINT",
        "REAL",
        "DOUBLE",
        "FLOAT",
        "DECIMAL",
        "NUMERIC",
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


def get_db_connection_string(db_type: str, host: str, port: int, database: str, username: str, password: str) -> str:
    """
    构建数据库连接字符串。

    Args:
        db_type: 数据库类型 (postgresql, mysql)
        host: 主机地址
        port: 端口
        database: 数据库名
        username: 用户名
        password: 密码

    Returns:
        数据库连接字符串
    """
    if db_type == "postgresql":
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    elif db_type == "mysql":
        return f"mysql://{username}:{password}@{host}:{port}/{database}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

