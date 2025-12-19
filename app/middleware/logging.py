"""
日志中间件

记录每个请求的详细信息，包括请求方法、路径、耗时、响应状态码等
"""
# mypy: ignore-errors

import time
from collections.abc import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class LoggingMiddleware(BaseHTTPMiddleware):
    """HTTP 请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并记录日志

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: 响应对象
        """
        # 记录请求开始时间
        start_time = time.time()

        # 获取请求信息
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else "unknown"

        # 记录请求开始
        logger.info(f"📨 {method} {url} - Client: {client_host}")

        # 处理请求
        try:
            response = await call_next(request)

            # 计算处理时间
            process_time = time.time() - start_time

            # 根据状态码使用不同的日志级别
            status_code = response.status_code
            log_msg = f"✅ {method} {url} - Status: {status_code} - Time: {process_time:.3f}s"

            if status_code >= 500:
                logger.error(log_msg)
            elif status_code >= 400:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            # 添加响应时间头
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time

            # 记录异常
            logger.exception(f"❌ {method} {url} - Error: {str(e)} - Time: {process_time:.3f}s")

            # 重新抛出异常，让 FastAPI 的异常处理器处理
            raise


def setup_logging():
    """
    配置 loguru 日志

    设置日志格式、级别、输出文件等
    日志级别根据环境自动调整：
    - development: 默认 DEBUG
    - production: 默认 INFO
    """
    # 移除默认的 handler
    logger.remove()

    # 获取有效的日志级别
    log_level = settings.effective_log_level

    # 添加控制台输出（带颜色）
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
    )

    # 添加文件输出（所有日志）
    logger.add(
        "logs/app.log",
        rotation="100 MB",  # 文件大小达到 100MB 时轮转
        retention="30 days",  # 保留 30 天的日志
        compression="zip",  # 压缩旧日志
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=log_level,
    )

    # 添加错误日志文件
    logger.add(
        "logs/error.log",
        rotation="50 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",
    )

    logger.info(f"✅ 日志系统初始化完成 (环境: {settings.ENVIRONMENT}, 日志级别: {log_level})")
