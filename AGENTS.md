# AI 编程助手指南

## 项目概述

**Fast Data Agent** 是一个基于 LangGraph 的 AI 数据分析平台，支持多种数据源配置，通过对话式交互进行数据分析。

## 项目架构

```
app/
├── api/              # 路由层：HTTP 请求处理
├── services/         # 服务层：业务逻辑
├── repositories/     # 数据层：数据库 CRUD
├── models/           # SQLAlchemy ORM 模型
├── schemas/          # Pydantic 验证模型
├── core/             # 配置、安全、异常、加密
├── utils/            # 工具函数和 Agent 工具
└── main.py           # 应用入口

web/                  # React 前端
├── src/
│   ├── api/          # API 客户端（自动生成）
│   ├── components/   # UI 组件
│   ├── pages/        # 页面组件
│   ├── hooks/        # 自定义 Hooks
│   └── types/        # TypeScript 类型
└── deploy.sh         # 前端构建脚本

sandbox_runtime/      # Python 沙盒服务（Docker）
├── main.py           # 沙盒 FastAPI 应用
└── Dockerfile        # 容器镜像

scripts/              # 工具脚本
├── e2e_flow.py       # 端到端测试
├── reset_resources.py # 资源重置
└── create_superuser.py # 创建管理员
```

## 核心数据模型

### User（用户）
- 基础用户信息、密码加密存储
- 关联：DatabaseConnection[], UploadedFile[], AnalysisSession[]

### DatabaseConnection（数据库连接）
- 支持：MySQL, PostgreSQL
- 包含：加密的连接凭证、连接测试

### RawData（数据对象）
- 类型：`database_table`（库表）或 `file`（文件）
- 包含：Schema 缓存、字段元数据、预览数据

### AnalysisSession（分析会话）
- 通过 SessionRawData 关联多个 RawData
- 包含：消息列表、任务推荐

### ChatMessage（对话消息）
- 角色：`human`, `ai`, `tool`, `system`
- 包含：工具调用、Artifact（图表/数据表）

### TaskRecommendation（任务推荐）
- 分类：`overview`, `trend`, `comparison`, `anomaly`, `correlation`, `distribution`

## 开发规范

### 分层职责
- **Router**: 参数验证、调用 Service、返回 `BaseResponse`
- **Service**: 业务逻辑、调用 Repository
- **Repository**: 数据库 CRUD（异步 SQLAlchemy）

### 响应格式
```python
BaseResponse(success=True, code=200, msg="成功", data=result)
```

### 异常处理
- `NotFoundException` → 404
- `BadRequestException` → 400
- `UnauthorizedException` → 401
- `ForbiddenException` → 403

### 数据库
- 异步 SQLAlchemy 2.0 + PostgreSQL
- 模型继承 `BaseTableMixin`（id, create_by, update_by, create_time, update_time, deleted）
- 软删除：`deleted=1`
- UUID 主键

### 文件存储
- MinIO 对象存储
- Bucket：`data-agent`

## 常用命令

```bash
# 后端开发
make install          # 安装依赖
make dev              # 启动后端 (port: 8000)
make check            # lint + format + type-check

# 前端开发
cd web && pnpm dev    # 启动前端 (port: 5173)
cd web && pnpm build  # 构建生产版本

# 沙盒管理
make sandbox-build    # 构建镜像
make sandbox-start    # 启动沙盒 (port: 8888)
make sandbox-restart  # 重启沙盒
make sandbox-status   # 查看状态

# 测试
make test             # 运行测试
make reset            # 重置资源（数据库、MinIO、沙盒）
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL |
| 对象存储 | MinIO |
| AI Agent | LangGraph + LangChain |
| LLM | OpenAI API |
| 前端框架 | React + TypeScript |
| UI 组件 | shadcn/ui + Tailwind CSS |
| 图表 | Plotly |

## Agent 工具

| 工具 | 功能 |
|------|------|
| `list_local_files` | 列出会话文件 |
| `quick_analysis` | 快速分析数据概况 |
| `execute_sql` | 执行 DuckDB SQL |
| `execute_python` | 执行 Python 代码 |
| `generate_chart` | 生成 Plotly 图表 |

## 沙盒服务 API

| 端点 | 功能 |
|------|------|
| `GET /files` | 列出会话文件 |
| `POST /upload` | 上传文件 |
| `GET /download/{path}` | 下载文件 |
| `POST /execute_python` | 执行 Python |
| `POST /execute_sql` | 执行 SQL |
| `POST /quick_analysis` | 快速分析 |
| `POST /generate_chart` | 生成图表 |

## 注意事项

- JWT 双令牌：access_token (30分钟) + refresh_token (7天)
- 密码使用 AES 加密存储
- SQL 执行在沙盒中隔离运行
- 沙盒启动命令：`make sandbox-start`
