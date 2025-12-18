"""
沙箱运行时 - 工具函数

包含文件操作、路径管理等通用工具
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

# ==================== 常量定义 ====================

SANDBOX_ROOT = Path("/app")

# MinIO 配置（从环境变量读取）
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


# ==================== 路径管理函数 ====================


def get_session_dir(user_id: str, thread_id: str) -> Path:
    """
    获取会话目录路径。

    Args:
        user_id: 用户 ID
        thread_id: 会话/线程 ID

    Returns:
        会话目录的 Path 对象
    """
    return SANDBOX_ROOT / "sessions" / str(user_id) / str(thread_id)


def ensure_session_dir(user_id: str, thread_id: str) -> Path:
    """
    确保会话目录存在。

    Args:
        user_id: 用户 ID
        thread_id: 会话/线程 ID

    Returns:
        会话目录的 Path 对象
    """
    session_dir = get_session_dir(user_id, thread_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def generate_unique_filename(directory: Path, prefix: str, ext: str) -> str:
    """
    生成唯一文件名（4 个随机字母）。

    Args:
        directory: 目标目录
        prefix: 文件名前缀（如 "sql_result_"）
        ext: 文件扩展名（如 ".parquet"，含点号）

    Returns:
        唯一的文件名（如 "sql_result_abcd.parquet"）
    """
    import random
    import string
    import time

    for _ in range(100):  # 最多尝试 100 次
        suffix = "".join(random.choices(string.ascii_lowercase, k=4))
        filename = f"{prefix}{suffix}{ext}"
        if not (directory / filename).exists():
            return filename

    # 如果 100 次都冲突，使用时间戳兜底
    return f"{prefix}{int(time.time())}{ext}"


# ==================== 文件操作函数 ====================


def list_files_in_dir(directory: Path) -> list[dict[str, Any]]:
    """
    列出目录中的所有文件。

    Args:
        directory: 要列出的目录

    Returns:
        文件信息列表，每个元素包含：
        - name: 文件名
        - size: 文件大小（字节）
        - modified: 修改时间（ISO 格式）
        - type: 文件类型（基于扩展名）
    """
    if not directory.exists():
        return []

    files = []
    for item in directory.iterdir():
        if item.is_file():
            stat = item.stat()
            files.append(
                {
                    "name": item.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": get_file_type(item.name),
                }
            )
    return sorted(files, key=lambda x: x["modified"], reverse=True)


def get_file_type(filename: str) -> str:
    """
    根据文件扩展名推断文件类型。

    Args:
        filename: 文件名

    Returns:
        文件类型字符串
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    type_map = {
        "csv": "csv",
        "parquet": "parquet",
        "json": "json",
        "xlsx": "excel",
        "xls": "excel",
        "png": "image",
        "jpg": "image",
        "jpeg": "image",
        "gif": "image",
        "svg": "image",
        "html": "html",
        "py": "python",
        "sql": "sql",
        "txt": "text",
        "md": "markdown",
    }
    return type_map.get(ext, "unknown")

