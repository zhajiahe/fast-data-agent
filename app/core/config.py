"""
配置管理模块

使用 Pydantic Settings 管理应用配置，支持从 .env 文件加载配置
"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 环境配置
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"

    # JWT 配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production"  # 生产环境必须更改
    REFRESH_SECRET_KEY: str = "your-refresh-secret-key-here-change-in-production"  # 生产环境必须更改
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 访问令牌过期时间（分钟）
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 刷新令牌过期时间（天）

    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres123@localhost:5432/data_agent"

    # MinIO 对象存储配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "admin"
    MINIO_SECRET_KEY: str = "admin123"
    MINIO_BUCKET: str = "data-agent"
    MINIO_SECURE: bool = False  # 是否使用 HTTPS

    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # 应用配置
    APP_NAME: str = "Fast Data Agent"
    DEBUG: bool = True

    # CORS 配置
    ALLOWED_ORIGINS: list[str] = ["*"]

    # AI/LLM 配置
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "OPENAI_MODEL"
    LLM_MODEL: str = "google/gemini-2.0-flash-exp:free"

    # Python 沙箱配置
    SANDBOX_URL: str = "http://localhost:8080"  # 沙箱服务地址
    SANDBOX_ENABLED: bool = True
    SANDBOX_TIMEOUT: int = 60  # 执行超时（秒）
    SANDBOX_MEMORY_LIMIT: str = "512m"  # 内存限制

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT == "production"

    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.ENVIRONMENT == "testing"


# 创建全局配置实例
settings = Settings()
