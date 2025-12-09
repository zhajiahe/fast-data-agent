"""
Pydantic Schema 模块

用于 API 请求和响应的数据验证和序列化
"""

from app.schemas.data_source import (
    DataSourceCreate,
    DataSourceListQuery,
    DataSourcePreviewRequest,
    DataSourcePreviewResponse,
    DataSourceResponse,
    DataSourceUpdate,
    FieldMapping,
    RawMappingResponse,
    TargetField,
)
from app.schemas.database_connection import (
    DatabaseConnectionConfig,
    DatabaseConnectionCreate,
    DatabaseConnectionResponse,
    DatabaseConnectionTablesResponse,
    DatabaseConnectionTestResult,
    DatabaseConnectionUpdate,
    DatabaseTableInfo,
)
from app.schemas.raw_data import (
    ColumnSchema,
    RawDataColumnUpdate,
    RawDataCreate,
    RawDataDatabaseTableConfig,
    RawDataFileConfig,
    RawDataListQuery,
    RawDataPreviewRequest,
    RawDataPreviewResponse,
    RawDataResponse,
    RawDataUpdate,
)
from app.schemas.user import (
    LoginRequest,
    PasswordChange,
    RefreshTokenRequest,
    UserCreate,
    UserListQuery,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListQuery",
    "PasswordChange",
    "LoginRequest",
    "RefreshTokenRequest",
    # DatabaseConnection
    "DatabaseConnectionConfig",
    "DatabaseConnectionCreate",
    "DatabaseConnectionUpdate",
    "DatabaseConnectionResponse",
    "DatabaseConnectionTestResult",
    "DatabaseConnectionTablesResponse",
    "DatabaseTableInfo",
    # RawData
    "ColumnSchema",
    "RawDataCreate",
    "RawDataUpdate",
    "RawDataColumnUpdate",
    "RawDataResponse",
    "RawDataListQuery",
    "RawDataPreviewRequest",
    "RawDataPreviewResponse",
    "RawDataDatabaseTableConfig",
    "RawDataFileConfig",
    # DataSource
    "TargetField",
    "FieldMapping",
    "DataSourceCreate",
    "DataSourceUpdate",
    "DataSourceResponse",
    "DataSourceListQuery",
    "DataSourcePreviewRequest",
    "DataSourcePreviewResponse",
    "RawMappingResponse",
]
