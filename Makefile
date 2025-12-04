.PHONY: help install dev test test-unit test-integration test-cov lint lint-fix format type-check check \
       db-migrate db-upgrade db-downgrade db-history db-current \
       docker-build docker-run docker-stop docker-dev clean pre-commit-install pre-commit-run \
       sandbox-build sandbox-start sandbox-stop sandbox-restart sandbox-status sandbox-logs

# 默认目标
.DEFAULT_GOAL := help

help: ## 显示帮助信息
	@echo "FastAPI Template - 可用命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

# ==================== 开发相关 ====================

install: ## 安装依赖
	@echo "📦 安装依赖..."
	uv sync

dev: ## 启动开发服务器
	@echo "🚀 启动开发服务器..."
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ==================== 测试相关 ====================

test: ## 运行所有测试
	@echo "🧪 运行所有测试..."
	uv run pytest tests/ -v

test-unit: ## 运行单元测试
	@echo "🧪 运行单元测试..."
	uv run pytest tests/unit/ -v -m unit

test-integration: ## 运行集成测试
	@echo "🧪 运行集成测试..."
	uv run pytest tests/integration/ -v -m integration

test-cov: ## 运行测试并生成覆盖率报告
	@echo "🧪 运行测试并生成覆盖率报告..."
	uv run pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# ==================== 代码质量 ====================

lint: ## 代码检查
	@echo "🔍 代码检查..."
	uv run ruff check app/ tests/

lint-fix: ## 代码检查并修复
	@echo "🔧 代码检查并修复..."
	uv run ruff check app/ tests/ --fix

format: ## 格式化代码
	@echo "🎨 格式化代码..."
	uv run ruff format app/ tests/

type-check: ## 类型检查
	@echo "🔍 类型检查..."
	uv run mypy app/

check: lint format type-check ## 运行所有检查（lint + format + type-check）
	@echo "✅ 所有检查完成"

# ==================== Pre-commit ====================

pre-commit-install: ## 安装 pre-commit hooks
	@echo "🔗 安装 pre-commit hooks..."
	uv run pre-commit install

pre-commit-run: ## 运行 pre-commit 检查
	@echo "🔍 运行 pre-commit 检查..."
	uv run pre-commit run --all-files

# ==================== 清理相关 ====================

clean: ## 清理临时文件
	@echo "🧹 清理临时文件..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✅ 清理完成"

# ==================== Sandbox 相关 ====================

SANDBOX_IMAGE := data-agent-sandbox
SANDBOX_CONTAINER := data-agent-sandbox
SANDBOX_PORT := 8080

sandbox-build: ## 构建 Sandbox Docker 镜像
	@echo "🔨 构建 Sandbox Docker 镜像..."
	docker build -t $(SANDBOX_IMAGE) sandbox_runtime/
	@echo "✅ 镜像构建完成: $(SANDBOX_IMAGE)"

sandbox-start: ## 启动 Sandbox 容器
	@echo "🚀 启动 Sandbox 容器..."
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
		echo "✅ Sandbox 已启动: http://localhost:$(SANDBOX_PORT)"; \
	fi

sandbox-stop: ## 停止 Sandbox 容器
	@echo "🛑 停止 Sandbox 容器..."
	@docker stop $(SANDBOX_CONTAINER) 2>/dev/null || true
	@docker rm $(SANDBOX_CONTAINER) 2>/dev/null || true
	@echo "✅ Sandbox 已停止"

sandbox-restart: sandbox-stop sandbox-start ## 重启 Sandbox 容器

sandbox-status: ## 查看 Sandbox 状态
	@echo "📊 Sandbox 状态:"
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

sandbox-logs: ## 查看 Sandbox 日志
	@echo "📜 Sandbox 日志 (Ctrl+C 退出):"
	docker logs -f $(SANDBOX_CONTAINER)
