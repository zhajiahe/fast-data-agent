"""
数据库连接器服务

提供数据库连接测试和 Schema 提取功能
"""

import time
from typing import Any

from loguru import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.core.exceptions import BadRequestException
from app.models.data_source import DatabaseType, DataSource, DataSourceType
from app.schemas.data_source import (
    ColumnSchema,
    DataSourceSchemaResponse,
    DataSourceTestResult,
    TableSchema,
)


class DBConnectorService:
    """数据库连接器服务"""

    # 数据库驱动映射
    DRIVER_MAP = {
        DatabaseType.MYSQL: "mysql+pymysql",
        DatabaseType.POSTGRESQL: "postgresql+psycopg2",
        DatabaseType.SQLITE: "sqlite",
        DatabaseType.MSSQL: "mssql+pymssql",
        DatabaseType.ORACLE: "oracle+cx_oracle",
        DatabaseType.CLICKHOUSE: "clickhouse+native",
        DatabaseType.DORIS: "mysql+pymysql",  # Doris 兼容 MySQL 协议
        DatabaseType.STARROCKS: "mysql+pymysql",  # StarRocks 兼容 MySQL 协议
    }

    def _build_connection_url(self, data_source: DataSource) -> str:
        """
        构建数据库连接 URL

        Args:
            data_source: 数据源配置

        Returns:
            连接 URL
        """
        if data_source.source_type != DataSourceType.DATABASE.value:
            raise BadRequestException(msg="只有数据库类型的数据源才能进行连接测试")

        db_type = DatabaseType(data_source.db_type)
        driver = self.DRIVER_MAP.get(db_type)

        if not driver:
            raise BadRequestException(msg=f"不支持的数据库类型: {db_type}")

        # SQLite 特殊处理
        if db_type == DatabaseType.SQLITE:
            return f"{driver}:///{data_source.database}"

        # 构建标准 URL
        url = f"{driver}://{data_source.username}:{data_source.password}@{data_source.host}:{data_source.port}/{data_source.database}"

        # 添加额外参数
        if data_source.extra_params:
            params = "&".join(f"{k}={v}" for k, v in data_source.extra_params.items())
            url += f"?{params}"

        return url

    def _create_engine(self, data_source: DataSource) -> Engine:
        """
        创建数据库引擎

        Args:
            data_source: 数据源配置

        Returns:
            SQLAlchemy 引擎
        """
        url = self._build_connection_url(data_source)
        return create_engine(url, pool_pre_ping=True, pool_size=1, max_overflow=0)

    async def test_connection(self, data_source: DataSource) -> DataSourceTestResult:
        """
        测试数据库连接

        Args:
            data_source: 数据源配置

        Returns:
            测试结果
        """
        try:
            engine = self._create_engine(data_source)
            start_time = time.time()

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            latency_ms = int((time.time() - start_time) * 1000)
            engine.dispose()

            return DataSourceTestResult(
                success=True,
                message="连接成功",
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return DataSourceTestResult(
                success=False,
                message=f"连接失败: {str(e)}",
                latency_ms=None,
            )

    async def extract_schema(self, data_source: DataSource) -> DataSourceSchemaResponse:
        """
        提取数据库 Schema

        Args:
            data_source: 数据源配置

        Returns:
            Schema 信息
        """
        try:
            engine = self._create_engine(data_source)
            inspector = inspect(engine)
            tables: list[TableSchema] = []

            for table_name in inspector.get_table_names():
                columns: list[ColumnSchema] = []
                pk_columns = set(inspector.get_pk_constraint(table_name).get("constrained_columns", []))

                for col in inspector.get_columns(table_name):
                    columns.append(
                        ColumnSchema(
                            name=col["name"],
                            data_type=str(col["type"]),
                            nullable=col.get("nullable", True),
                            primary_key=col["name"] in pk_columns,
                            comment=col.get("comment"),
                        )
                    )

                # 获取表注释
                table_comment = self._get_table_comment(inspector, table_name)

                # 获取行数估算
                row_count = self._get_row_count_estimate(engine, table_name)

                tables.append(
                    TableSchema(
                        name=table_name,
                        columns=columns,
                        row_count=row_count,
                        comment=table_comment,
                    )
                )

            engine.dispose()

            return DataSourceSchemaResponse(tables=tables)
        except Exception as e:
            logger.error(f"Schema extraction failed: {e}")
            raise BadRequestException(msg=f"Schema 提取失败: {str(e)}") from e

    def _get_table_comment(self, inspector: Any, table_name: str) -> str | None:
        """获取表注释"""
        try:
            comment: str | None = inspector.get_table_comment(table_name).get("text")
            return comment
        except Exception:
            return None

    def _get_row_count_estimate(self, engine: Engine, table_name: str) -> int | None:
        """获取行数估算"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name} LIMIT 1"))  # noqa: S608
                return result.scalar()
        except Exception:
            return None

    async def execute_query(
        self,
        data_source: DataSource,
        query: str,
        limit: int = 1000,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """
        执行 SQL 查询

        Args:
            data_source: 数据源配置
            query: SQL 查询
            limit: 最大返回行数

        Returns:
            (数据行列表, 列名列表)
        """
        try:
            engine = self._create_engine(data_source)

            with engine.connect() as conn:
                result = conn.execute(text(query))
                columns = list(result.keys())
                rows = [dict(zip(columns, row, strict=False)) for row in result.fetchmany(limit)]

            engine.dispose()
            return rows, columns
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise BadRequestException(msg=f"查询执行失败: {str(e)}") from e
