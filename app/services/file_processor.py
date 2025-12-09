"""
文件处理器服务

处理 CSV、Excel、JSON、Parquet 文件的解析和元数据提取
"""

from io import BytesIO
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
    }

    # MIME 类型映射
    MIME_MAP = {
        "text/csv": FileType.CSV,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": FileType.EXCEL,
        "application/vnd.ms-excel": FileType.EXCEL,
        "application/json": FileType.JSON,
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
                        "name": str(col),  # 确保列名是字符串
                        "dtype": col_type,
                        "type": simple_type,
                        "nullable": bool(df[col].isnull().any()),  # 转换为 Python 原生 bool
                        "unique_count": int(df[col].nunique()),
                    }
                )

            # 生成预览数据
            preview_df = df.head(preview_rows)
            # 将 DataFrame 转换为字典，然后手动处理 NaN
            # to_dict() 会保留 NaN，需要在 _convert_to_native_types 中处理
            preview_data = cls._convert_to_native_types(preview_df.to_dict(orient="records"))

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
    def _convert_to_native_types(cls, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        将数据中的 numpy 类型转换为 Python 原生类型

        Args:
            data: 包含可能是 numpy 类型的字典列表

        Returns:
            转换后的数据
        """
        import math

        import numpy as np

        def convert_value(val: Any) -> Any:
            if val is None:
                return None
            # 检查 pandas/numpy NaN
            if isinstance(val, float) and (math.isnan(val) or val != val):
                return None
            if isinstance(val, np.bool_):
                return bool(val)
            if isinstance(val, np.integer):
                return int(val)
            if isinstance(val, np.floating):
                return None if np.isnan(val) else float(val)
            if isinstance(val, np.ndarray):
                return val.tolist()
            # 处理 pandas Timestamp
            if hasattr(val, "isoformat"):
                return val.isoformat()
            return val

        return [{k: convert_value(v) for k, v in row.items()} for row in data]

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
