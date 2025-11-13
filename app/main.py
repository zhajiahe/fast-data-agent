"""
FastAPI 应用主入口

提供应用配置、路由注册和中间件设置
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.users import router as users_router
from app.core.lifespan import lifespan

# 创建 FastAPI 应用
app = FastAPI(
    title="FastAPI Template",
    description="基于 SQLAlchemy 2.0+ 的 FastAPI 项目模板",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
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
        "message": "FastAPI Template is running!",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "message": "Application is running"}


# 注册用户路由
app.include_router(users_router, prefix="/api/v1")


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
