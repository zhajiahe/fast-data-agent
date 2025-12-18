"""
简单的对称加解密工具，用于敏感字段（如数据库密码）加密存储。
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

from app.core.config import settings


class DecryptionError(Exception):
    """解密失败异常"""

    pass


def _get_fernet() -> Fernet:
    """
    使用 SECRET_KEY 派生一个 32 字节的 key 以生成 Fernet 实例。

    Fernet 要求 key 为 32 字节的 urlsafe base64 编码。
    """
    key_material = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)


def encrypt_str(plain: str) -> str:
    """对字符串进行对称加密，返回加密后的字符串。"""
    f = _get_fernet()
    return f.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_str(cipher: str, *, allow_plaintext: bool = False) -> str:
    """
    解密字符串。

    Args:
        cipher: 加密后的字符串
        allow_plaintext: 是否允许明文（解密失败时返回原文）

    Returns:
        解密后的字符串

    Raises:
        DecryptionError: 解密失败且不允许明文时抛出
    """
    f = _get_fernet()
    try:
        return f.decrypt(cipher.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as e:
        if allow_plaintext:
            logger.warning(f"解密失败，返回原文（可能是未加密的明文）: {e}")
            return cipher
        raise DecryptionError(f"解密失败: {e}") from e
