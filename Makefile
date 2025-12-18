.PHONY: help install dev test lint lint-fix format type-check check clean reset \
       sandbox-build sandbox-start sandbox-stop sandbox-restart sandbox-status sandbox-logs \
       web-dev web-build web-lint

# 默认目标
.DEFAULT_GOAL := help

help: ## 显示帮助信息
	@echo "Fast Data Agent - 可用命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

# ==================== 后端开发 ====================

install: ## 安装后端依赖
	@echo "📦 安装依赖..."
	uv sync

dev: ## 启动后端开发服务器 (port: 8000)
	@echo "🚀 启动后端服务器..."
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --no-access-log

test: ## 运行所有测试
	@echo "🧪 运行测试..."
	uv run pytest tests/ -v

lint: ## 后端代码检查
	@echo "🔍 代码检查..."
	uv run ruff check app/

lint-fix: ## 后端代码检查并修复
	@echo "🔧 代码检查并修复..."
	uv run ruff check app/ --fix

format: ## 格式化后端代码
	@echo "🎨 格式化代码..."
	uv run ruff format app/

type-check: ## 类型检查
	@echo "🔍 类型检查..."
	uv run mypy app/

check: lint format type-check ## 运行所有检查
	@echo "✅ 后端检查完成"

# ==================== 前端开发 ====================

web-dev: ## 启动前端开发服务器 (port: 5173)
	@echo "🚀 启动前端服务器..."
	cd web && pnpm dev

web-build: ## 构建前端生产版本
	@echo "🔨 构建前端..."
	cd web && bash deploy.sh

web-lint: ## 前端代码检查
	@echo "🔍 前端代码检查..."
	cd web && pnpm lint

# ==================== 清理与重置 ====================

clean: ## 清理临时文件
	@echo "🧹 清理临时文件..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@truncate -s 0 logs/*.log 2>/dev/null || true
	@echo "✅ 清理完成"

reset: ## 重置所有资源（数据库、MinIO、沙盒）
	@echo "🔄 重置所有资源..."
	@echo "yes" | uv run python scripts/reset_resources.py

# ==================== 沙盒管理 ====================

SANDBOX_IMAGE := data-agent-sandbox
SANDBOX_CONTAINER := data-agent-sandbox
SANDBOX_PORT := 8888

sandbox-build: ## 构建沙盒 Docker 镜像
	@echo "🔨 构建沙盒镜像..."
	docker build -t $(SANDBOX_IMAGE) sandbox_runtime/
	@echo "✅ 镜像构建完成: $(SANDBOX_IMAGE)"

sandbox-start: ## 启动沙盒容器 (port: 8888)
	@echo "🚀 启动沙盒容器..."
	@if docker ps -q -f name=$(SANDBOX_CONTAINER) | grep -q .; then \
		echo "⚠️  容器已在运行"; \
	else \
		docker run -d --name $(SANDBOX_CONTAINER) \
			-p $(SANDBOX_PORT):8888 \
			-e MINIO_ENDPOINT=host.docker.internal:9000 \
			-e MINIO_ACCESS_KEY=admin \
			-e MINIO_SECRET_KEY=admin123 \
			-e MINIO_SECURE=false \
			--add-host=host.docker.internal:host-gateway \
			$(SANDBOX_IMAGE); \
		echo "✅ 沙盒已启动: http://localhost:$(SANDBOX_PORT)"; \
	fi

sandbox-stop: ## 停止沙盒容器
	@echo "🛑 停止沙盒容器..."
	@docker stop $(SANDBOX_CONTAINER) 2>/dev/null || true
	@docker rm $(SANDBOX_CONTAINER) 2>/dev/null || true
	@echo "✅ 沙盒已停止"

sandbox-restart: sandbox-stop sandbox-start ## 重启沙盒容器

sandbox-status: ## 查看沙盒状态
	@echo "📊 沙盒状态:"
	@echo ""
	@if docker ps -q -f name=$(SANDBOX_CONTAINER) | grep -q .; then \
		echo "  状态: ✅ 运行中"; \
		echo "  地址: http://localhost:$(SANDBOX_PORT)"; \
		echo ""; \
		docker ps --filter name=$(SANDBOX_CONTAINER) --format "table {{.ID}}\t{{.Status}}\t{{.Ports}}"; \
	else \
		echo "  状态: ❌ 未运行"; \
		echo ""; \
		echo "  使用 'make sandbox-start' 启动"; \
	fi

sandbox-logs: ## 查看沙盒日志
	@echo "📜 沙盒日志 (Ctrl+C 退出):"
	docker logs -f $(SANDBOX_CONTAINER)
