"""
数据库连接器服务

提供数据库连接测试和 Schema 提取功能
"""

import hashlib
import time
from typing import Any, ClassVar

from loguru import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.core.encryption import decrypt_str
from app.core.exceptions import BadRequestException
from app.models.database_connection import DatabaseConnection, DatabaseType
from app.schemas.database_connection import DatabaseConnectionTestResult


class EngineCache:
    """
    数据库引擎缓存

    缓存 SQLAlchemy Engine 实例以复用连接池，避免每次操作都创建新引擎。
    使用连接配置的哈希值作为缓存键。
    """

    def __init__(self, max_size: int = 20, ttl_seconds: int = 3600):
        """
        初始化缓存

        Args:
            max_size: 最大缓存引擎数量
            ttl_seconds: 缓存过期时间（秒）
        """
        self._cache: dict[str, tuple[Engine, float]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def _make_key(self, connection: DatabaseConnection) -> str:
        """生成缓存键"""
        # 使用连接配置的关键字段生成哈希
        key_parts = [
            str(connection.id),
            connection.db_type,
            connection.host,
            str(connection.port),
            connection.database,
            connection.username,
            connection.password,  # 加密后的密码
        ]
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def get(self, connection: DatabaseConnection) -> Engine | None:
        """获取缓存的引擎"""
        key = self._make_key(connection)
        if key in self._cache:
            engine, created_at = self._cache[key]
            # 检查是否过期
            if time.time() - created_at < self._ttl:
                return engine
            # 过期则移除
            self._remove(key)
        return None

    def put(self, connection: DatabaseConnection, engine: Engine) -> None:
        """缓存引擎"""
        # 清理过期条目
        self._cleanup_expired()

        # 如果超过最大数量，移除最旧的
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            self._remove(oldest_key)

        key = self._make_key(connection)
        self._cache[key] = (engine, time.time())

    def remove(self, connection: DatabaseConnection) -> None:
        """移除缓存的引擎"""
        key = self._make_key(connection)
        self._remove(key)

    def _remove(self, key: str) -> None:
        """移除指定键的引擎"""
        if key in self._cache:
            engine, _ = self._cache.pop(key)
            try:
                engine.dispose()
            except Exception as e:
                logger.warning(f"Error disposing engine: {e}")

    def _cleanup_expired(self) -> None:
        """清理过期条目"""
        now = time.time()
        expired_keys = [k for k, (_, created_at) in self._cache.items() if now - created_at >= self._ttl]
        for key in expired_keys:
            self._remove(key)

    def clear(self) -> None:
        """清空所有缓存"""
        for key in list(self._cache.keys()):
            self._remove(key)


# 全局引擎缓存实例
_engine_cache = EngineCache()


class DBConnectorService:
    """数据库连接器服务"""

    # 数据库驱动映射
    DRIVER_MAP: ClassVar[dict[DatabaseType, str]] = {
        DatabaseType.MYSQL: "mysql+pymysql",
        DatabaseType.POSTGRESQL: "postgresql+psycopg2",
    }

    def _build_connection_url(self, connection: DatabaseConnection) -> str:
        """
        构建数据库连接 URL

        Args:
            connection: 数据库连接配置

        Returns:
            连接 URL
        """
        db_type = DatabaseType(connection.db_type)
        driver = self.DRIVER_MAP.get(db_type)

        if not driver:
            raise BadRequestException(msg=f"不支持的数据库类型: {db_type}")

        password = decrypt_str(connection.password, allow_plaintext=True)

        # 构建标准 URL
        url = f"{driver}://{connection.username}:{password}@{connection.host}:{connection.port}/{connection.database}"

        # 添加额外参数
        if connection.extra_params:
            params = "&".join(f"{k}={v}" for k, v in connection.extra_params.items())
            url += f"?{params}"

        return url

    def _get_engine(self, connection: DatabaseConnection, *, use_cache: bool = True) -> Engine:
        """
        获取数据库引擎（优先从缓存获取）

        Args:
            connection: 数据库连接配置
            use_cache: 是否使用缓存（测试连接时可能需要新引擎）

        Returns:
            SQLAlchemy 引擎
        """
        if use_cache:
            cached = _engine_cache.get(connection)
            if cached:
                return cached

        url = self._build_connection_url(connection)
        engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,  # 增加连接池大小
            max_overflow=10,  # 允许额外连接
            pool_recycle=3600,  # 1小时回收连接
        )

        if use_cache:
            _engine_cache.put(connection, engine)

        return engine

    def _create_engine(self, connection: DatabaseConnection) -> Engine:
        """
        创建数据库引擎（兼容性方法，内部使用 _get_engine）

        Args:
            connection: 数据库连接配置

        Returns:
            SQLAlchemy 引擎
        """
        return self._get_engine(connection)

    async def test_database_connection(self, connection: DatabaseConnection) -> DatabaseConnectionTestResult:
        """
        测试数据库连接

        Args:
            connection: 数据库连接配置

        Returns:
            测试结果
        """
        try:
            # 测试连接时不使用缓存，确保测试的是新连接
            engine = self._get_engine(connection, use_cache=False)
            start_time = time.time()

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            latency_ms = int((time.time() - start_time) * 1000)

            # 测试成功后将引擎加入缓存
            _engine_cache.put(connection, engine)

            return DatabaseConnectionTestResult(
                success=True,
                message="连接成功",
                latency_ms=latency_ms,
            )
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return DatabaseConnectionTestResult(
                success=False,
                message=f"连接失败: {str(e)}",
                latency_ms=None,
            )

    async def get_tables(self, connection: DatabaseConnection) -> list[dict[str, Any]]:
        """
        获取数据库表列表

        Args:
            connection: 数据库连接配置

        Returns:
            表信息列表
        """
        try:
            engine = self._create_engine(connection)
            inspector = inspect(engine)
            tables: list[dict[str, Any]] = []

            # 获取所有 schema
            schemas = inspector.get_schema_names()

            for schema in schemas:
                # 跳过系统 schema
                if schema in ("information_schema", "pg_catalog", "pg_toast"):
                    continue

                # 获取表
                for table_name in inspector.get_table_names(schema=schema):
                    comment = self._get_table_comment(inspector, table_name, schema)
                    tables.append(
                        {
                            "schema": schema,
                            "name": table_name,
                            "type": "TABLE",
                            "comment": comment,
                        }
                    )

                # 获取视图
                for view_name in inspector.get_view_names(schema=schema):
                    tables.append(
                        {
                            "schema": schema,
                            "name": view_name,
                            "type": "VIEW",
                            "comment": None,
                        }
                    )

            # 引擎由缓存管理，不需要手动 dispose
            return tables
        except Exception as e:
            logger.error(f"Get tables failed: {e}")
            raise BadRequestException(msg=f"获取表列表失败: {str(e)}") from e

    async def get_table_schema(
        self,
        connection: DatabaseConnection,
        *,
        schema_name: str | None = None,
        table_name: str | None = None,
    ) -> dict[str, Any]:
        """
        获取表结构信息

        Args:
            connection: 数据库连接配置
            schema_name: Schema 名称
            table_name: 表名

        Returns:
            表结构信息
        """
        if not table_name:
            raise BadRequestException(msg="必须提供表名")

        try:
            engine = self._create_engine(connection)
            inspector = inspect(engine)

            columns: list[dict[str, Any]] = []
            pk_columns = set(inspector.get_pk_constraint(table_name, schema=schema_name).get("constrained_columns", []))

            for col in inspector.get_columns(table_name, schema=schema_name):
                columns.append(
                    {
                        "name": col["name"],
                        "data_type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "primary_key": col["name"] in pk_columns,
                        "comment": col.get("comment"),
                    }
                )

            # 获取行数估算
            row_count = self._get_row_count_estimate(engine, table_name, schema=schema_name)

            # 引擎由缓存管理，不需要手动 dispose
            return {
                "columns": columns,
                "row_count": row_count,
            }
        except Exception as e:
            logger.error(f"Get table schema failed: {e}")
            raise BadRequestException(msg=f"获取表结构失败: {str(e)}") from e

    async def preview_table(
        self,
        connection: DatabaseConnection,
        *,
        schema_name: str | None = None,
        table_name: str | None = None,
        custom_sql: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        预览表数据

        Args:
            connection: 数据库连接配置
            schema_name: Schema 名称
            table_name: 表名
            custom_sql: 自定义 SQL
            limit: 行数限制

        Returns:
            预览数据
        """
        try:
            engine = self._create_engine(connection)

            # 构建查询
            if custom_sql:
                query = f"SELECT * FROM ({custom_sql}) AS subq LIMIT {limit}"  # noqa: S608
            elif table_name:
                full_table = f"{schema_name}.{table_name}" if schema_name else table_name
                query = f"SELECT * FROM {full_table} LIMIT {limit}"  # noqa: S608
            else:
                raise BadRequestException(msg="必须提供 table_name 或 custom_sql")

            with engine.connect() as conn:
                result = conn.execute(text(query))
                column_names = list(result.keys())
                rows = [dict(zip(column_names, row, strict=False)) for row in result.fetchall()]

            # 获取列信息
            columns: list[dict[str, Any]] = []
            if table_name:
                inspector = inspect(engine)
                for col in inspector.get_columns(table_name, schema=schema_name):
                    columns.append(
                        {
                            "name": col["name"],
                            "data_type": str(col["type"]),
                            "nullable": col.get("nullable", True),
                        }
                    )
            else:
                # 从结果推断列信息
                for col_name in column_names:
                    columns.append(
                        {
                            "name": col_name,
                            "data_type": "unknown",
                            "nullable": True,
                        }
                    )

            # 获取总行数
            total_rows = None
            if table_name:
                total_rows = self._get_row_count_estimate(engine, table_name, schema=schema_name)

            # 引擎由缓存管理，不需要手动 dispose
            return {
                "columns": columns,
                "rows": rows,
                "total_rows": total_rows,
            }
        except Exception as e:
            logger.error(f"Preview table failed: {e}")
            raise BadRequestException(msg=f"预览数据失败: {str(e)}") from e

    async def execute_query(
        self,
        connection: DatabaseConnection,
        query: str,
        limit: int = 1000,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """
        执行 SQL 查询

        Args:
            connection: 数据库连接配置
            query: SQL 查询
            limit: 最大返回行数

        Returns:
            (数据行列表, 列名列表)
        """
        try:
            engine = self._create_engine(connection)

            with engine.connect() as conn:
                result = conn.execute(text(query))
                columns = list(result.keys())
                rows = [dict(zip(columns, row, strict=False)) for row in result.fetchmany(limit)]

            # 引擎由缓存管理，不需要手动 dispose
            return rows, columns
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise BadRequestException(msg=f"查询执行失败: {str(e)}") from e

    def _get_table_comment(self, inspector: Any, table_name: str, schema: str | None = None) -> str | None:
        """获取表注释"""
        try:
            comment: str | None = inspector.get_table_comment(table_name, schema=schema).get("text")
            return comment
        except Exception:
            return None

    def _get_row_count_estimate(self, engine: Engine, table_name: str, *, schema: str | None = None) -> int | None:
        """获取行数估算"""
        try:
            full_table = f"{schema}.{table_name}" if schema else table_name
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {full_table} LIMIT 1")  # noqa: S608
                )
                return result.scalar()
        except Exception:
            return None
