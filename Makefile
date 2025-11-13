.PHONY: help install dev test lint format clean db-init db-migrate db-upgrade db-downgrade pre-commit-install

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## 显示帮助信息
	@echo "$(BLUE)FastAPI Template - 可用命令:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## 安装项目依赖
	@echo "$(BLUE)📦 安装项目依赖...$(NC)"
	uv sync
	@echo "$(GREEN)✅ 依赖安装完成$(NC)"

dev: ## 启动开发服务器
	@echo "$(BLUE)🚀 启动开发服务器...$(NC)"
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-debug: ## 启动开发服务器（调试模式）
	@echo "$(BLUE)🐛 启动调试模式服务器...$(NC)"
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

test: ## 运行所有测试
	@echo "$(BLUE)🧪 运行测试...$(NC)"
	uv run pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-unit: ## 运行单元测试
	@echo "$(BLUE)🧪 运行单元测试...$(NC)"
	uv run pytest tests/unit/ -v

test-integration: ## 运行集成测试
	@echo "$(BLUE)🧪 运行集成测试...$(NC)"
	uv run pytest tests/integration/ -v

test-e2e: ## 运行端到端测试
	@echo "$(BLUE)🧪 运行端到端测试...$(NC)"
	uv run pytest tests/e2e/ -v

test-watch: ## 监听模式运行测试
	@echo "$(BLUE)👀 监听模式运行测试...$(NC)"
	uv run pytest-watch tests/ -v

lint: ## 运行代码检查
	@echo "$(BLUE)🔍 运行代码检查...$(NC)"
	uv run ruff check app/ tests/
	@echo "$(GREEN)✅ 代码检查完成$(NC)"

lint-fix: ## 运行代码检查并自动修复
	@echo "$(BLUE)🔧 运行代码检查并自动修复...$(NC)"
	uv run ruff check app/ tests/ --fix
	@echo "$(GREEN)✅ 代码修复完成$(NC)"

format: ## 格式化代码
	@echo "$(BLUE)🎨 格式化代码...$(NC)"
	uv run ruff format app/ tests/
	@echo "$(GREEN)✅ 代码格式化完成$(NC)"

type-check: ## 运行类型检查
	@echo "$(BLUE)🔍 运行类型检查...$(NC)"
	uv run mypy app/
	@echo "$(GREEN)✅ 类型检查完成$(NC)"

check: lint format type-check ## 运行所有检查（lint + format + type-check）
	@echo "$(GREEN)✅ 所有检查完成$(NC)"

pre-commit-install: ## 安装 pre-commit hooks
	@echo "$(BLUE)🔗 安装 pre-commit hooks...$(NC)"
	uv run pre-commit install
	@echo "$(GREEN)✅ pre-commit hooks 安装完成$(NC)"

pre-commit-run: ## 运行 pre-commit 检查所有文件
	@echo "$(BLUE)🔍 运行 pre-commit 检查...$(NC)"
	uv run pre-commit run --all-files

db-init: ## 初始化数据库
	@echo "$(BLUE)🗄️  初始化数据库...$(NC)"
	uv run alembic init alembic
	@echo "$(GREEN)✅ 数据库初始化完成$(NC)"

db-migrate: ## 创建数据库迁移（需要提供消息: make db-migrate msg="描述"）
	@echo "$(BLUE)📝 创建数据库迁移...$(NC)"
	@if [ -z "$(msg)" ]; then \
		echo "$(RED)❌ 错误: 请提供迁移消息，例如: make db-migrate msg=\"add user table\"$(NC)"; \
		exit 1; \
	fi
	uv run alembic revision --autogenerate -m "$(msg)"
	@echo "$(GREEN)✅ 迁移文件创建完成$(NC)"

db-upgrade: ## 升级数据库到最新版本
	@echo "$(BLUE)⬆️  升级数据库...$(NC)"
	uv run alembic upgrade head
	@echo "$(GREEN)✅ 数据库升级完成$(NC)"

db-downgrade: ## 降级数据库一个版本
	@echo "$(YELLOW)⬇️  降级数据库...$(NC)"
	uv run alembic downgrade -1
	@echo "$(GREEN)✅ 数据库降级完成$(NC)"

db-history: ## 显示数据库迁移历史
	@echo "$(BLUE)📜 数据库迁移历史:$(NC)"
	uv run alembic history

db-current: ## 显示当前数据库版本
	@echo "$(BLUE)📍 当前数据库版本:$(NC)"
	uv run alembic current

db-reset: ## 重置数据库（危险操作！）
	@echo "$(RED)⚠️  警告: 这将删除所有数据！$(NC)"
	@read -p "确定要重置数据库吗？(y/N) " confirm; \
	if [ "$$confirm" = "y" ]; then \
		uv run alembic downgrade base; \
		uv run alembic upgrade head; \
		echo "$(GREEN)✅ 数据库重置完成$(NC)"; \
	else \
		echo "$(YELLOW)❌ 操作已取消$(NC)"; \
	fi

clean: ## 清理临时文件
	@echo "$(BLUE)🧹 清理临时文件...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	rm -rf coverage.xml 2>/dev/null || true
	@echo "$(GREEN)✅ 清理完成$(NC)"

clean-all: clean ## 清理所有生成文件（包括 uv 锁文件）
	@echo "$(BLUE)🧹 深度清理...$(NC)"
	rm -rf .venv/ 2>/dev/null || true
	@echo "$(GREEN)✅ 深度清理完成$(NC)"

shell: ## 进入 Python shell
	@echo "$(BLUE)🐍 启动 Python shell...$(NC)"
	uv run python

shell-ipython: ## 进入 IPython shell
	@echo "$(BLUE)🐍 启动 IPython shell...$(NC)"
	uv run ipython

requirements: ## 导出依赖到 requirements.txt
	@echo "$(BLUE)📋 导出依赖...$(NC)"
	uv pip compile pyproject.toml -o requirements.txt
	@echo "$(GREEN)✅ 依赖已导出到 requirements.txt$(NC)"

docker-build: ## 构建 Docker 镜像
	@echo "$(BLUE)🐳 构建 Docker 镜像...$(NC)"
	docker build -t fastapi-template:latest .
	@echo "$(GREEN)✅ Docker 镜像构建完成$(NC)"

docker-run: ## 运行 Docker 容器
	@echo "$(BLUE)🐳 运行 Docker 容器...$(NC)"
	docker run -d -p 8000:8000 --name fastapi-template fastapi-template:latest
	@echo "$(GREEN)✅ Docker 容器已启动$(NC)"

docker-stop: ## 停止 Docker 容器
	@echo "$(BLUE)🐳 停止 Docker 容器...$(NC)"
	docker stop fastapi-template
	docker rm fastapi-template
	@echo "$(GREEN)✅ Docker 容器已停止$(NC)"

logs: ## 查看应用日志
	@echo "$(BLUE)📋 应用日志:$(NC)"
	tail -f logs/app.log

info: ## 显示项目信息
	@echo "$(BLUE)ℹ️  项目信息:$(NC)"
	@echo "项目名称: FastAPI Template"
	@echo "Python 版本: $$(python --version)"
	@echo "uv 版本: $$(uv --version)"
	@echo "FastAPI 版本: $$(uv run python -c 'import fastapi; print(fastapi.__version__)')"
	@echo "SQLAlchemy 版本: $$(uv run python -c 'import sqlalchemy; print(sqlalchemy.__version__)')"
