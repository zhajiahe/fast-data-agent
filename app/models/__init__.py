"""
SQLAlchemy数据模型模块

包含所有数据库表模型的定义
"""

from app.models.session import AnalysisSession
from app.models.base import Base, BasePageQuery, BaseResponse, BaseTableMixin, PageResponse, Token, TokenPayload
from app.models.message import ChatMessage, MessageType
from app.models.data_source import DatabaseType, DataSource, DataSourceType, FileType
from app.models.recommendation import (
    RecommendationCategory,
    RecommendationSourceType,
    RecommendationStatus,
    TaskRecommendation,
)
from app.models.uploaded_file import UploadedFile
from app.models.user import User

__all__ = [
    # Base
    "Base",
    "BaseTableMixin",
    "BaseResponse",
    "BasePageQuery",
    "PageResponse",
    "Token",
    "TokenPayload",
    # User
    "User",
    # DataSource
    "DataSource",
    "DataSourceType",
    "DatabaseType",
    "FileType",
    # UploadedFile
    "UploadedFile",
    # AnalysisSession
    "AnalysisSession",
    # TaskRecommendation
    "TaskRecommendation",
    "RecommendationCategory",
    "RecommendationSourceType",
    "RecommendationStatus",
    # ChatMessage
    "ChatMessage",
    "MessageType",
]
