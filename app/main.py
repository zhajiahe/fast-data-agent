"""
FastAPI 应用主入口

提供应用配置、路由注册和中间件设置
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api.chat import router as chat_router
from app.api.data_sources import router as data_sources_router
from app.api.database_connections import router as database_connections_router
from app.api.files import router as files_router
from app.api.raw_data import router as raw_data_router
from app.api.recommendations import router as recommendations_router
from app.api.sessions import router as sessions_router
from app.api.users import auth_router
from app.api.users import router as users_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.middleware.logging import LoggingMiddleware, setup_logging

# 设置日志
setup_logging()

# 创建 FastAPI 应用
app = FastAPI(
    title="Fast Data Agent",
    description="基于 LangGraph 的 AI 数据分析平台",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 注册全局异常处理器
register_exception_handlers(app)

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 配置 CORS（从配置文件读取允许的来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
@app.get("/", tags=["Root"])
async def root():
    """根路径，健康检查"""
    return {
        "status": "ok",
        "message": "Fast Data Agent is running!",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "message": "Application is running"}


# 注册认证路由
app.include_router(auth_router, prefix="/api/v1")

# 注册用户路由
app.include_router(users_router, prefix="/api/v1")

# 注册数据库连接路由
app.include_router(database_connections_router, prefix="/api/v1")

# 注册原始数据路由
app.include_router(raw_data_router, prefix="/api/v1")

# 注册数据源路由
app.include_router(data_sources_router, prefix="/api/v1")

# 注册文件路由
app.include_router(files_router, prefix="/api/v1")

# 注册会话路由
app.include_router(sessions_router, prefix="/api/v1")

# 注册对话路由
app.include_router(chat_router, prefix="/api/v1")

# 注册推荐路由
app.include_router(recommendations_router, prefix="/api/v1")

# 挂载前端静态文件
# 前端构建产物目录（相对于项目根目录）
WEB_DIST_DIR = Path(__file__).parent.parent / "web" / "dist"
if WEB_DIST_DIR.exists():
    # 挂载静态资源（CSS、JS、图片等）
    app.mount("/web/assets", StaticFiles(directory=str(WEB_DIST_DIR / "assets")), name="web_assets")
    logger.info(f"前端静态文件已挂载到 /web，目录: {WEB_DIST_DIR}")

    # SPA 回退路由 - 所有 /web/* 路径都返回 index.html
    @app.get("/web/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """SPA 路由回退，所有非静态资源请求都返回 index.html"""
        # 检查是否请求静态文件
        file_path = WEB_DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # 否则返回 index.html（SPA 回退）
        return FileResponse(WEB_DIST_DIR / "index.html")

    @app.get("/web")
    async def serve_spa_root():
        """SPA 根路径"""
        return FileResponse(WEB_DIST_DIR / "index.html")
else:
    logger.warning(f"前端静态文件目录不存在: {WEB_DIST_DIR}，跳过挂载")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI application...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式自动重载
        log_level="info",
    )
