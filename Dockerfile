# =================================
# Fast Data Agent - Dockerfile
# =================================
# 使用多阶段构建优化镜像大小

# ========== 基础阶段 ==========
FROM python:3.12-slim AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# 创建非 root 用户
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# 设置工作目录
WORKDIR /app

# ========== 构建阶段 ==========
FROM base AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN uv sync --frozen --no-cache --no-dev

# ========== 运行阶段 ==========
FROM base AS runtime

# 复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 设置 PATH
ENV PATH="/app/.venv/bin:$PATH"

# 复制应用代码
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser scripts/ ./scripts/

# 创建日志目录
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"]

# ========== 开发阶段 ==========
FROM runtime AS development

# 切换回 root 安装开发依赖
USER root

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装开发依赖
RUN uv sync --frozen --no-cache

# 切换回 appuser
USER appuser

# 启动开发服务器
CMD ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]

