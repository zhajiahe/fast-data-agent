# Fast Data Agent

> 基于 LangGraph 的 AI 数据分析平台

## ✨ 特性

- 🤖 **LangGraph Agent** - 智能数据分析助手
- 🗄️ **多数据源支持** - MySQL, PostgreSQL, 文件等
- 📊 **智能推荐** - 自动生成分析任务推荐
- 💬 **对话式分析** - 自然语言驱动的数据探索
- 📈 **可视化** - Plotly 前端图表渲染
- 🔒 **安全执行** - Python 代码沙箱隔离

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     前端 (React + Plotly)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ 数据源管理    │  │ 分析会话界面  │  │ 图表/表格可视化      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │ API
┌─────────────────────────────────────────────────────────────────┐
│                     后端 (FastAPI + LangGraph)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    LangGraph Agent                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │ Schema 分析器 │  │ SQL/代码生成  │  │ 任务推荐器   │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ 数据源服务    │  │ 会话服务      │  │ 执行引擎 (沙箱)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         数据层                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ PostgreSQL   │  │ MinIO        │  │ 用户数据源            │  │
│  │ (元数据存储)  │  │ (文件存储)    │  │ (MySQL/PG/文件等)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 项目结构

```
fast-data-agent/
├── app/
│   ├── api/              # API 路由
│   ├── core/             # 配置、安全、数据库
│   ├── models/           # SQLAlchemy 模型
│   │   ├── user.py           # 用户模型
│   │   ├── data_source.py    # 数据源配置
│   │   ├── uploaded_file.py  # 上传文件
│   │   ├── analysis_session.py  # 分析会话
│   │   ├── chat_message.py   # 对话消息
│   │   └── task_recommendation.py  # 任务推荐
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 业务逻辑层
│   ├── repositories/     # 数据访问层
│   ├── utils/            # 工具函数和 Agent 工具
│   └── main.py           # 应用入口
├── sandbox_runtime/      # Python 沙盒服务
│   ├── main.py           # 沙盒 FastAPI 应用
│   ├── Dockerfile        # 沙盒容器镜像
│   └── requirements.txt  # 沙盒依赖
├── scripts/              # 脚本工具
│   ├── test_user_flow.py     # 用户流程测试
│   └── reset_resources.py    # 资源重置脚本
├── tests/                # 测试代码
├── alembic/              # 数据库迁移
└── docker-compose.yml    # Docker Compose
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.12+
- PostgreSQL 16+
- MinIO (或 S3 兼容存储)
- OpenAI API Key (或兼容 API)

### 2. 安装依赖

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆并安装
git clone <your-repo-url>
cd fast-data-agent
uv sync
```

### 3. 配置环境变量

```bash
cp env.example .env
# 编辑 .env 配置数据库、MinIO、OpenAI 等
```

### 4. 初始化数据库

```bash
# 创建迁移
alembic revision --autogenerate -m "init"

# 执行迁移
alembic upgrade head
```

### 5. 启动服务

```bash
make dev
# 访问 http://localhost:8000/docs
```

## 🗄️ 数据模型

```
User (用户)
├── DataSource[] (数据源配置)
│   ├── 数据库连接 (MySQL/PostgreSQL/ClickHouse...)
│   └── 文件引用 -> UploadedFile
├── UploadedFile[] (上传文件 -> MinIO)
└── AnalysisSession[] (分析会话)
    ├── ChatMessage[] (对话历史)
    │   ├── 用户消息
    │   ├── AI 回复
    │   └── 工具调用结果
    └── TaskRecommendation[] (任务推荐)
```

## 🔄 核心流程

```
1. 配置数据源          2. 创建分析会话           3. 对话式分析
┌──────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│ • 添加数据库  │  →   │ • 选择数据源      │  →   │ • 系统推荐分析任务   │
│ • 上传文件   │      │ • 提取 Schema     │      │ • 用户自由提问       │
└──────────────┘      └──────────────────┘      │ • AI 生成 SQL/代码   │
                                                │ • 执行并可视化结果   │
                                                │ • 推荐追问问题       │
                                                └─────────────────────┘
                                                         ↑________↓
                                                        (循环分析)
```

## 🛠️ 常用命令

```bash
# 开发
make dev              # 启动开发服务器
make test             # 运行测试
make check            # 代码质量检查 (lint + format + type-check)

# 数据库
make db-migrate msg="xxx"  # 数据库迁移

# 沙盒管理
make sandbox-build    # 构建沙盒 Docker 镜像
make sandbox-start    # 启动沙盒容器
make sandbox-stop     # 停止沙盒容器
make sandbox-restart  # 重启沙盒容器
make sandbox-status   # 查看沙盒状态
make sandbox-logs     # 查看沙盒日志

# 资源管理
make reset            # 重置所有资源（数据库、MinIO、沙盒）
```

## 🐳 Docker 部署

```bash
# 仅应用（使用外部 PostgreSQL/MinIO）
docker compose up -d app

# 完整环境（包含 PostgreSQL/MinIO）
docker compose --profile infra up -d
```

## 📄 License

MIT License
