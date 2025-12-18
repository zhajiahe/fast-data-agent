"""
沙箱运行时 - 文件服务

包含文件操作和会话管理功能
"""

import shutil
import logging
from pathlib import Path
from typing import Any

from sandbox_runtime.utils import (
    SANDBOX_ROOT,
    get_session_dir,
    ensure_session_dir,
    list_files_in_dir,
)

logger = logging.getLogger(__name__)


class FileService:
    """文件操作服务"""

    @staticmethod
    def reset_session(user_id: str, thread_id: str) -> dict[str, Any]:
        """
        重置指定会话的文件。
        删除该会话目录下的所有文件。

        Args:
            user_id: 用户 ID
            thread_id: 会话 ID

        Returns:
            操作结果
        """
        session_dir = get_session_dir(user_id, thread_id)

        if not session_dir.exists():
            return {
                "success": True,
                "message": "Session directory does not exist, nothing to clean",
                "deleted_count": 0,
            }

        try:
            # 统计文件数量
            files = list_files_in_dir(session_dir)
            deleted_count = len(files)

            # 删除目录内容
            shutil.rmtree(session_dir)
            session_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Reset session: user_id={user_id}, thread_id={thread_id}, deleted={deleted_count} files")

            return {
                "success": True,
                "message": "Session reset successfully",
                "deleted_count": deleted_count,
            }
        except Exception as e:
            logger.exception(f"Failed to reset session: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def reset_user(user_id: str) -> dict[str, Any]:
        """
        重置指定用户的所有会话文件。
        删除该用户目录下的所有文件。

        Args:
            user_id: 用户 ID

        Returns:
            操作结果
        """
        user_dir = SANDBOX_ROOT / "sessions" / str(user_id)

        if not user_dir.exists():
            return {
                "success": True,
                "message": "User directory does not exist, nothing to clean",
                "deleted_count": 0,
                "session_count": 0,
            }

        try:
            # 统计会话和文件数量
            session_count = len([d for d in user_dir.iterdir() if d.is_dir()])
            file_count = 0
            for session_dir in user_dir.iterdir():
                if session_dir.is_dir():
                    file_count += len(list_files_in_dir(session_dir))

            # 删除用户目录
            shutil.rmtree(user_dir)

            logger.info(f"Reset user: user_id={user_id}, deleted={file_count} files in {session_count} sessions")

            return {
                "success": True,
                "message": "User data reset successfully",
                "deleted_count": file_count,
                "session_count": session_count,
            }
        except Exception as e:
            logger.exception(f"Failed to reset user: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def reset_all() -> dict[str, Any]:
        """
        重置所有沙盒数据。
        删除 sessions 目录下的所有文件。

        Returns:
            操作结果
        """
        sessions_dir = SANDBOX_ROOT / "sessions"

        if not sessions_dir.exists():
            return {
                "success": True,
                "message": "Sessions directory does not exist, nothing to clean",
                "deleted_count": 0,
                "user_count": 0,
            }

        try:
            # 统计用户和文件数量
            user_count = len([d for d in sessions_dir.iterdir() if d.is_dir()])
            file_count = 0
            for user_dir in sessions_dir.iterdir():
                if user_dir.is_dir():
                    for session_dir in user_dir.iterdir():
                        if session_dir.is_dir():
                            file_count += len(list_files_in_dir(session_dir))

            # 删除整个 sessions 目录并重建
            shutil.rmtree(sessions_dir)
            sessions_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Reset all: deleted={file_count} files from {user_count} users")

            return {
                "success": True,
                "message": "All sandbox data reset successfully",
                "deleted_count": file_count,
                "user_count": user_count,
            }
        except Exception as e:
            logger.exception(f"Failed to reset all: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_session_files(user_id: str, thread_id: str) -> list[dict[str, Any]]:
        """
        列出会话目录中的所有文件。

        Args:
            user_id: 用户 ID
            thread_id: 会话 ID

        Returns:
            文件信息列表
        """
        session_dir = get_session_dir(user_id, thread_id)
        return list_files_in_dir(session_dir)

    @staticmethod
    def save_uploaded_file(user_id: str, thread_id: str, filename: str, content: bytes) -> Path:
        """
        保存上传的文件到会话目录。

        Args:
            user_id: 用户 ID
            thread_id: 会话 ID
            filename: 文件名
            content: 文件内容

        Returns:
            保存的文件路径
        """
        session_dir = ensure_session_dir(user_id, thread_id)
        file_path = session_dir / filename

        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Uploaded file: {file_path}, size={len(content)} bytes")
        return file_path

    @staticmethod
    def get_file_path(user_id: str, thread_id: str, file_path: str) -> Path | None:
        """
        获取会话中的文件完整路径。

        Args:
            user_id: 用户 ID
            thread_id: 会话 ID
            file_path: 相对文件路径

        Returns:
            文件完整路径，如果文件不存在或路径非法则返回 None
        """
        session_dir = get_session_dir(user_id, thread_id)
        full_path = session_dir / file_path

        # 安全检查：防止路径穿越
        try:
            full_path.resolve().relative_to(session_dir.resolve())
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {file_path}")
            return None

        if not full_path.exists():
            return None

        return full_path

