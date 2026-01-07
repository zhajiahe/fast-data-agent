"""
SQLAlchemy数据模型模块

包含所有数据库表模型的定义
"""

from app.models.base import Base, BasePageQuery, BaseResponse, BaseTableMixin, PageResponse, Token, TokenPayload
from app.models.database_connection import DatabaseConnection, DatabaseType
from app.models.message import ChatMessage, MessageType
from app.models.raw_data import RawData, RawDataType
from app.models.recommendation import (
    RecommendationCategory,
    RecommendationSourceType,
    RecommendationStatus,
    TaskRecommendation,
)
from app.models.session import AnalysisSession, SessionRawData
from app.models.uploaded_file import FileType, UploadedFile
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
    # DatabaseConnection
    "DatabaseConnection",
    "DatabaseType",
    # RawData
    "RawData",
    "RawDataType",
    # UploadedFile
    "UploadedFile",
    "FileType",
    # AnalysisSession
    "AnalysisSession",
    "SessionRawData",
    # TaskRecommendation
    "TaskRecommendation",
    "RecommendationCategory",
    "RecommendationSourceType",
    "RecommendationStatus",
    # ChatMessage
    "ChatMessage",
    "MessageType",
]
