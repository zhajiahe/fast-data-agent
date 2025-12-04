"""
文件处理器服务

处理 CSV、Excel、JSON、Parquet、SQLite 文件的解析和元数据提取
"""

import sqlite3
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from app.core.exceptions import BadRequestException
from app.models.data_source import FileType


class FileProcessorService:
    """文件处理器服务"""

    # 文件扩展名映射
    EXTENSION_MAP = {
        ".csv": FileType.CSV,
        ".xlsx": FileType.EXCEL,
        ".xls": FileType.EXCEL,
        ".json": FileType.JSON,
        ".parquet": FileType.PARQUET,
        ".db": FileType.SQLITE,
        ".sqlite": FileType.SQLITE,
        ".sqlite3": FileType.SQLITE,
    }

    # MIME 类型映射
    MIME_MAP = {
        "text/csv": FileType.CSV,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.EXCEL,
        "application/vnd.ms-excel": FileType.EXCEL,
        "application/json": FileType.JSON,
        "application/x-sqlite3": FileType.SQLITE,
        "application/vnd.sqlite3": FileType.SQLITE,
        "application/octet-stream": None,  # 需要通过扩展名判断
    }

    @classmethod
    def detect_file_type(cls, filename: str, mime_type: str | None = None) -> FileType:
        """
        检测文件类型

        Args:
            filename: 文件名
            mime_type: MIME 类型

        Returns:
            文件类型
        """
        # 先尝试通过 MIME 类型判断
        if mime_type and mime_type in cls.MIME_MAP:
            file_type = cls.MIME_MAP[mime_type]
            if file_type:
                return file_type

        # 通过扩展名判断
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in cls.EXTENSION_MAP:
            return cls.EXTENSION_MAP[ext]

        raise BadRequestException(msg=f"不支持的文件类型: {filename}")

    @classmethod
    async def parse_file(
        cls,
        data: bytes,
        file_type: FileType,
        preview_rows: int = 100,
    ) -> dict[str, Any]:
        """
        解析文件并提取元数据

        Args:
            data: 文件内容
            file_type: 文件类型
            preview_rows: 预览行数

        Returns:
            包含元数据和预览数据的字典
        """
        try:
            # SQLite 文件需要特殊处理
            if file_type == FileType.SQLITE:
                return await cls._parse_sqlite(data, preview_rows)

            df = cls._read_dataframe(data, file_type)

            # 提取列信息
            columns_info = []
            for col in df.columns:
                col_type = str(df[col].dtype)
                # 简化类型
                if "int" in col_type:
                    simple_type = "integer"
                elif "float" in col_type:
                    simple_type = "float"
                elif "datetime" in col_type:
                    simple_type = "datetime"
                elif "bool" in col_type:
                    simple_type = "boolean"
                else:
                    simple_type = "string"

                columns_info.append(
                    {
                        "name": col,
                        "dtype": col_type,
                        "type": simple_type,
                        "nullable": df[col].isnull().any(),
                        "unique_count": int(df[col].nunique()),
                    }
                )

            # 生成预览数据
            preview_df = df.head(preview_rows)
            # 将 NaN 转换为 None
            preview_data = preview_df.where(pd.notnull(preview_df), None).to_dict(orient="records")

            return {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns_info": columns_info,
                "preview_data": preview_data,
            }
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"File parsing failed: {e}")
            raise BadRequestException(msg=f"文件解析失败: {str(e)}") from e

    @classmethod
    async def _parse_sqlite(cls, data: bytes, preview_rows: int = 100) -> dict[str, Any]:
        """
        解析 SQLite 数据库文件

        Args:
            data: SQLite 文件内容
            preview_rows: 预览行数

        Returns:
            包含表信息和预览数据的字典
        """
        # 写入临时文件
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            f.write(data)
            temp_path = f.name

        try:
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()

            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

            if not tables:
                raise BadRequestException(msg="SQLite 数据库中没有表")

            # 获取第一个表的信息作为主要数据（与其他文件类型保持一致）
            main_table = tables[0]

            # 获取行数
            cursor.execute(f"SELECT COUNT(*) FROM '{main_table}'")  # noqa: S608
            row_count = cursor.fetchone()[0]

            # 获取列信息
            cursor.execute(f"PRAGMA table_info('{main_table}')")  # noqa: S608
            columns_meta = cursor.fetchall()

            columns_info = []
            for col in columns_meta:
                col_name = col[1]
                col_type = col[2] or "TEXT"
                nullable = col[3] == 0  # notnull 字段

                # 简化类型
                col_type_upper = col_type.upper()
                if "INT" in col_type_upper:
                    simple_type = "integer"
                elif "REAL" in col_type_upper or "FLOAT" in col_type_upper or "DOUBLE" in col_type_upper:
                    simple_type = "float"
                elif "BLOB" in col_type_upper:
                    simple_type = "binary"
                else:
                    simple_type = "string"

                columns_info.append({
                    "name": col_name,
                    "dtype": col_type,
                    "type": simple_type,
                    "nullable": nullable,
                })

            # 获取预览数据
            cursor.execute(f"SELECT * FROM '{main_table}' LIMIT {preview_rows}")  # noqa: S608
            rows = cursor.fetchall()
            column_names = [col[1] for col in columns_meta]
            preview_data = [dict(zip(column_names, row, strict=False)) for row in rows]

            conn.close()

            return {
                "row_count": row_count,
                "column_count": len(columns_meta),
                "columns_info": columns_info,
                "preview_data": preview_data,
                "tables": tables,  # 额外信息：所有表名
                "main_table": main_table,
            }
        finally:
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)

    @classmethod
    def _read_dataframe(cls, data: bytes, file_type: FileType) -> pd.DataFrame:
        """读取数据为 DataFrame"""
        buffer = BytesIO(data)

        if file_type == FileType.CSV:
            return pd.read_csv(buffer)
        elif file_type == FileType.EXCEL:
            return pd.read_excel(buffer)
        elif file_type == FileType.JSON:
            return pd.read_json(buffer)
        elif file_type == FileType.PARQUET:
            return pd.read_parquet(buffer)
        else:
            raise BadRequestException(msg=f"不支持的文件类型: {file_type}")

    @classmethod
    async def get_preview(
        cls,
        data: bytes,
        file_type: FileType,
        rows: int = 100,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        """
        获取文件预览

        Args:
            data: 文件内容
            file_type: 文件类型
            rows: 预览行数

        Returns:
            (列信息, 数据行, 总行数)
        """
        df = cls._read_dataframe(data, file_type)

        # 列信息
        columns = [{"name": col, "type": str(df[col].dtype)} for col in df.columns]

        # 预览数据
        preview_df = df.head(rows)
        data_rows = preview_df.where(pd.notnull(preview_df), None).to_dict(orient="records")

        return columns, data_rows, len(df)
