"""
自定义异常和全局异常处理器

统一处理应用中的各种异常，返回一致的错误响应格式
"""

import traceback
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import ValidationError

from app.core.config import settings


class AppException(Exception):
    """应用自定义异常基类"""

    def __init__(
        self,
        code: int = 400,
        msg: str = "请求错误",
        detail: Any = None,
    ):
        self.code = code
        self.msg = msg
        self.detail = detail
        super().__init__(msg)


class NotFoundException(AppException):
    """资源未找到异常"""

    def __init__(self, msg: str = "资源不存在", detail: Any = None):
        super().__init__(code=404, msg=msg, detail=detail)


class UnauthorizedException(AppException):
    """未授权异常"""

    def __init__(self, msg: str = "未授权访问", detail: Any = None):
        super().__init__(code=401, msg=msg, detail=detail)


class ForbiddenException(AppException):
    """禁止访问异常"""

    def __init__(self, msg: str = "禁止访问", detail: Any = None):
        super().__init__(code=403, msg=msg, detail=detail)


class BadRequestException(AppException):
    """错误请求异常"""

    def __init__(self, msg: str = "请求参数错误", detail: Any = None):
        super().__init__(code=400, msg=msg, detail=detail)


class ConflictException(AppException):
    """资源冲突异常"""

    def __init__(self, msg: str = "资源冲突", detail: Any = None):
        super().__init__(code=409, msg=msg, detail=detail)


def create_error_response(
    code: int,
    msg: str,
    detail: Any = None,
) -> JSONResponse:
    """创建统一的错误响应"""
    return JSONResponse(
        status_code=code,
        content={
            "success": False,
            "code": code,
            "msg": msg,
            "data": None,
            "err": detail,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """处理自定义应用异常"""
        logger.warning(f"AppException: {exc.msg} - Detail: {exc.detail}")
        return create_error_response(
            code=exc.code,
            msg=exc.msg,
            detail=exc.detail,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """处理 HTTP 异常"""
        logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
        return create_error_response(
            code=exc.status_code,
            msg=str(exc.detail),
            detail=None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """处理请求验证错误"""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(
                {
                    "field": field,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
        logger.warning(f"ValidationError: {errors}")
        return create_error_response(
            code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            msg="请求参数验证失败",
            detail=errors,
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """处理 Pydantic 验证错误"""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(
                {
                    "field": field,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
        logger.warning(f"PydanticValidationError: {errors}")
        return create_error_response(
            code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            msg="数据验证失败",
            detail=errors,
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        处理未捕获的异常

        开发环境返回详细错误信息和堆栈，生产环境只返回通用错误消息
        """
        logger.exception(f"Unhandled exception: {exc}")

        # 开发环境返回详细错误信息
        if settings.is_development:
            detail = {
                "error": str(exc),
                "type": type(exc).__name__,
                "traceback": traceback.format_exc(),
            }
        else:
            # 生产环境隐藏内部错误细节
            detail = None

        return create_error_response(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            msg="服务器内部错误",
            detail=detail,
        )
