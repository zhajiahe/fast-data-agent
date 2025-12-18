"""
配置管理模块

使用 Pydantic Settings 管理应用配置，支持从 .env 文件加载配置
"""

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 不安全的默认密钥，仅用于开发环境
_INSECURE_SECRET_KEYS = {
    "your-secret-key-here-change-in-production",
    "your-secret-key-change-in-production",
    "your-refresh-secret-key-here-change-in-production",
    "your-refresh-secret-key-change-in-production",
}


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

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """验证生产环境配置安全性"""
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY in _INSECURE_SECRET_KEYS:
                raise ValueError(
                    "生产环境禁止使用默认 SECRET_KEY，请设置安全的随机密钥。"
                    "可使用: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            if self.REFRESH_SECRET_KEY in _INSECURE_SECRET_KEYS:
                raise ValueError(
                    "生产环境禁止使用默认 REFRESH_SECRET_KEY，请设置安全的随机密钥。"
                )
            if self.DEBUG:
                raise ValueError("生产环境禁止开启 DEBUG 模式")
        return self

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
    DEBUG: bool = False

    # 默认管理员账号（用于初始化系统时创建）
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_NICKNAME: str = "Admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    # CORS 配置
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000", "http://localhost:3000", "http://localhost:5173"]

    # AI/LLM 配置
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "OPENAI_MODEL"
    LLM_MODEL: str = "google/gemini-2.0-flash-exp:free"
    LLM_STREAMING: bool = True  # 是否启用流式响应（OpenRouter 等代理可能需要禁用）

    # Python 沙箱配置
    SANDBOX_URL: str = "http://localhost:8888"  # 沙箱服务地址
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
