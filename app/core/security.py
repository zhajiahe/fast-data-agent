import hashlib
import os
import uuid
from datetime import datetime, timedelta

import bcrypt
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

# JWT认证方案
security = HTTPBearer()

# 安全配置
SECRET_KEY = settings.SECRET_KEY
REFRESH_SECRET_KEY = settings.REFRESH_SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# bcrypt rounds - 测试环境使用更少的rounds以提高速度
_BCRYPT_ROUNDS = 4 if os.getenv("TESTING") == "1" else 12


def get_password_hash(password: str) -> str:
    """使用 bcrypt 生成密码哈希"""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    hashed: bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    result: bool = bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    return result


def get_token_hash(token: str) -> str:
    """返回给定Token的哈希值"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_tokens(data: dict) -> tuple[str, str]:
    """创建访问令牌和刷新令牌"""
    # 将 UUID 转换为字符串以便 JSON 序列化
    serializable_data = {
        k: str(v) if isinstance(v, uuid.UUID) else v
        for k, v in data.items()
    }

    # 访问令牌
    access_expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_payload = serializable_data.copy()
    access_payload.update({"exp": access_expire, "type": "access"})
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)

    # 刷新令牌
    refresh_expire = datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_payload = serializable_data.copy()
    refresh_payload.update({"exp": refresh_expire, "type": "refresh"})
    refresh_token = jwt.encode(refresh_payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

    return access_token, refresh_token


def verify_access_token(token: str, credentials_exception) -> uuid.UUID:
    """验证访问令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        # 从令牌中获取用户ID并转换为UUID
        user_id_raw = payload.get("user_id")
        # 兼容旧 token 中的 int 类型 ID
        user_id_str = str(user_id_raw) if user_id_raw is not None else None
        if not user_id_str:
            raise credentials_exception
        return uuid.UUID(user_id_str)
    except (JWTError, ValueError) as e:
        raise credentials_exception from e


def verify_refresh_token(token: str, credentials_exception) -> uuid.UUID:
    """验证刷新令牌"""
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        # 从令牌中获取用户ID并转换为UUID
        user_id_raw = payload.get("user_id")
        # 兼容旧 token 中的 int 类型 ID
        user_id_str = str(user_id_raw) if user_id_raw is not None else None
        if not user_id_str:
            raise credentials_exception
        return uuid.UUID(user_id_str)
    except (JWTError, ValueError) as e:
        raise credentials_exception from e
