# Fast Data Agent

> 基于 LangGraph 的 AI 数据分析平台

## ✨ 特性

- 🤖 **LangGraph Agent** - 智能数据分析助手
- 🗄️ **多数据源支持** - MySQL, PostgreSQL, CSV, Excel 等
- 📊 **数据对象管理** - 独立管理库表和文件的原始数据
- 🔗 **灵活字段映射** - 多数据对象组合为统一数据源
- 💬 **对话式分析** - 自然语言驱动的数据探索
- 📈 **可视化** - Plotly 图表渲染
- 🔒 **安全执行** - Python/SQL 代码沙箱隔离

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     前端 (React + Plotly)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ 数据对象管理  │  │ 数据源配置    │  │ 对话分析界面          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │ API
┌─────────────────────────────────────────────────────────────────┐
│                     后端 (FastAPI + LangGraph)                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    LangGraph Agent                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │ execute_sql  │  │execute_python│  │ generate_chart│   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ 数据对象服务  │  │ 数据源服务    │  │ 沙盒执行引擎          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         数据层                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ PostgreSQL   │  │ MinIO        │  │ 用户数据库            │  │
│  │ (元数据存储)  │  │ (文件存储)    │  │ (MySQL/PG)           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 项目结构

```
fast-data-agent/
├── app/
│   ├── api/                    # API 路由
│   │   ├── database_connections.py  # 数据库连接管理
│   │   ├── raw_data.py              # 数据对象管理
│   │   ├── data_sources.py          # 数据源管理
│   │   ├── sessions.py              # 分析会话
│   │   └── chat.py                  # 对话接口
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── database_connection.py   # 数据库连接配置
│   │   ├── raw_data.py              # 数据对象（库表/文件）
│   │   ├── data_source.py           # 数据源 + 字段映射
│   │   ├── session.py               # 分析会话
│   │   └── message.py               # 对话消息
│   ├── services/               # 业务逻辑层
│   ├── repositories/           # 数据访问层
│   ├── schemas/                # Pydantic 验证模型
│   ├── core/                   # 配置、安全、数据库
│   └── utils/                  # 工具函数和 Agent 工具
├── sandbox_runtime/            # Python 沙盒服务 (Docker)
│   ├── main.py                 # 沙盒 FastAPI 应用
│   └── Dockerfile              # 沙盒容器镜像
├── web/                        # React 前端
│   └── src/
│       ├── pages/              # 页面组件
│       └── components/         # 通用组件
├── scripts/                    # 脚本工具
└── tests/                      # 测试代码
```

## 🗄️ 数据模型

项目采用三层数据架构：

```
DatabaseConnection (数据库连接)
  │ 1:N
  ▼
RawData (数据对象)                UploadedFile (上传文件)
  │ 可引用数据库表或文件              │
  │                               │
  └───────────── M:N ─────────────┘
                 │
                 ▼
        DataSourceRawMapping (字段映射)
                 │ N:1
                 ▼
           DataSource (数据源)
                 │ 1:N
                 ▼
         AnalysisSession (分析会话)
                 │ 1:N
                 ▼
           ChatMessage (对话消息)
```

### 核心概念

| 概念 | 说明 |
|------|------|
| **DatabaseConnection** | 数据库连接配置（MySQL/PostgreSQL），可被多个数据对象复用 |
| **RawData** | 数据对象，登记库表或文件的原始数据结构，包含列信息和预览数据 |
| **DataSource** | 数据源，基于多个数据对象构建，支持字段映射和聚合 |
| **AnalysisSession** | 分析会话，关联单个数据源进行对话式分析 |

## 🔄 核心流程

```
1. 配置数据库连接         2. 登记数据对象           3. 构建数据源
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ • 添加 MySQL/PG   │ →  │ • 选择连接+表      │ →  │ • 选择数据对象    │
│ • 测试连接        │    │ • 或上传文件       │    │ • 配置字段映射    │
└──────────────────┘    │ • 预览数据结构     │    │ • 预览合并结果    │
                        └──────────────────┘    └──────────────────┘
                                                         │
                                                         ▼
                        4. 对话分析
                        ┌─────────────────────────────────────┐
                        │ • 创建会话，选择数据源                 │
                        │ • 自然语言提问                        │
                        │ • AI 生成 SQL/Python 代码            │
                        │ • 沙盒执行，返回结果和图表             │
                        └─────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.12+
- PostgreSQL 16+
- MinIO (或 S3 兼容存储)
- Docker (用于沙盒服务)
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
# 执行迁移
alembic upgrade head
```

### 5. 启动服务

```bash
# 启动沙盒服务
make sandbox-build
make sandbox-start

# 启动后端
make dev
# 访问 http://localhost:8000/docs

# 启动前端（另一个终端）
cd web && npm install && npm run dev
# 访问 http://localhost:5173
```

## 🛠️ 常用命令

```bash
# 开发
make dev              # 启动后端开发服务器
make test             # 运行测试
make check            # 代码质量检查 (lint + format + type-check)

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

## 🔧 Agent 工具

| 工具 | 功能 |
|------|------|
| `execute_sql` | 在沙盒中执行 DuckDB SQL 查询 |
| `execute_python` | 在沙盒中执行 Python 代码（支持 pandas） |
| `quick_analysis` | 快速分析数据源概况 |
| `generate_chart` | 生成 Plotly 图表 |
| `list_local_files` | 列出沙盒中的会话文件 |

## 🐳 沙盒服务

沙盒运行在 Docker 容器中，提供隔离的代码执行环境：

| 端点 | 功能 |
|------|------|
| `POST /execute_sql` | 执行 DuckDB SQL |
| `POST /execute_python` | 执行 Python 代码 |
| `POST /quick_analysis` | 快速数据分析 |
| `POST /generate_chart` | 生成图表 |
| `GET /files` | 列出会话文件 |
| `POST /upload` | 上传文件到会话目录 |
| `GET /download/{path}` | 下载会话文件 |

## 📄 License

MIT License
