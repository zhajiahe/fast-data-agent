# AI 编程助手指南

## 项目概述

**Fast Data Agent** 是一个基于 LangGraph 的 AI 数据分析平台，用户可以配置多种数据源，通过对话式交互进行数据分析。

## 项目架构

```
app/
├── api/              # 路由层：处理 HTTP 请求
├── services/         # 服务层：业务逻辑
├── repositories/     # 数据层：数据库操作
├── models/           # SQLAlchemy 模型
├── schemas/          # Pydantic 验证模型
├── core/             # 配置、安全、异常
├── utils/            # 工具函数和 Agent 工具
└── main.py           # 应用入口

sandbox_runtime/      # Python 沙盒服务（Docker 容器）
├── main.py           # 沙盒 FastAPI 应用
└── Dockerfile        # 沙盒容器镜像

scripts/              # 脚本工具
├── test_user_flow.py     # 用户流程测试
└── reset_resources.py    # 资源重置脚本
```

## 核心数据模型

### User（用户）
- 基础用户信息
- 关联：DataSource[], UploadedFile[], AnalysisSession[]

### DataSource（数据源）
- 类型：`database`（数据库连接）或 `file`（文件引用）
- 数据库支持：MySQL, PostgreSQL, SQLite
- 包含：连接配置、Schema 缓存

### UploadedFile（上传文件）
- 存储位置：MinIO（对象存储）
- 文件类型：CSV, Excel, JSON, Parquet
- 包含：元数据、预览数据、处理状态

### AnalysisSession（分析会话）
- 关联多个数据源（`data_source_ids: Array`）
- 包含：会话配置、消息列表、任务推荐列表

### ChatMessage（对话消息）
- 角色：`user`, `assistant`, `system`, `tool`
- 类型：`text`, `sql`, `code`, `chart`, `table`, `error`, `tool_call`, `tool_result`
- 包含：SQL 查询/结果、工具调用信息、Token 统计

### TaskRecommendation（任务推荐）
- 分类：`overview`, `trend`, `comparison`, `anomaly`, `correlation`, `distribution`
- 状态：`pending`, `selected`, `dismissed`

## 开发规范

### 分层职责
- **Router**: 参数验证、调用 Service、返回响应
- **Service**: 业务逻辑、调用 Repository、调用 Agent
- **Repository**: 数据库 CRUD 操作
- **Agent**: LangGraph 智能体逻辑

### 响应格式
统一使用 `BaseResponse`:
```python
BaseResponse(success=True, code=200, msg="成功", data=result)
```

### 异常处理
使用自定义异常（自动转换为统一响应）:
- `NotFoundException` - 404
- `BadRequestException` - 400
- `UnauthorizedException` - 401
- `ForbiddenException` - 403

### 数据库
- 使用异步 SQLAlchemy + PostgreSQL
- 继承 `BaseTableMixin` 获取通用字段（id, create_by, update_by, create_time, update_time, deleted）
- 软删除：`deleted=1`
- JSONB 类型用于存储灵活数据

### 文件存储
- 使用 MinIO 对象存储
- 库：`miniopy-async`
- Bucket：`data-agent`

## 工作流程

1. **新增功能**: Schema → Model → Repository → Service → Router
2. **新增 Agent**: 在 `app/agents/` 下创建 LangGraph 图
3. **测试优先**: 先执行测试，再编写文档
4. **提交前**: `make check` 确保代码质量

## 常用命令

```bash
make dev              # 启动开发服务器
make test             # 运行测试
make check            # lint + format + type-check
make db-migrate msg="xxx"  # 数据库迁移

# 沙盒管理
make sandbox-build    # 构建沙盒镜像
make sandbox-start    # 启动沙盒
make sandbox-restart  # 重启沙盒
make sandbox-status   # 查看状态

# 资源重置
make reset            # 重置所有资源（数据库、MinIO、沙盒）
```

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL |
| 对象存储 | MinIO |
| AI Agent | LangGraph + LangChain |
| LLM | OpenAI API (可配置) |
| 数据处理 | Pandas, PyArrow |
| 前端可视化 | Plotly |

## Agent 工具

当前实现的 LangGraph Agent 工具（`app/utils/tools.py`）：

| 工具 | 功能 |
|------|------|
| `list_local_files` | 列出沙盒中的会话文件 |
| `quick_analysis` | 快速分析数据源概况 |
| `execute_sql` | 执行 DuckDB SQL 查询 |
| `execute_python` | 在沙盒中执行 Python 代码 |
| `generate_chart` | 生成 Plotly 图表 |

## 沙盒服务

沙盒服务运行在 Docker 容器中，提供以下 API：

| 端点 | 功能 |
|------|------|
| `GET /files` | 列出会话文件 |
| `POST /upload` | 上传文件到会话目录 |
| `GET /download/{path}` | 下载会话文件 |
| `POST /execute` | 执行 Shell 命令 |
| `POST /execute_python` | 执行 Python 代码 |
| `POST /execute_sql` | 执行 DuckDB SQL |
| `POST /quick_analysis` | 快速数据分析 |
| `POST /generate_chart` | 生成图表 |
| `POST /reset/session` | 重置会话文件 |
| `POST /reset/user` | 重置用户所有会话 |
| `POST /reset/all` | 重置全部沙盒数据 |

## 注意事项

- 密码传输使用 JSON Body，不用 Query 参数
- JWT 双令牌：access_token (30分钟) + refresh_token (7天)
- 管理员接口需要 `CurrentSuperUser` 依赖
- 数据源密码需要加密存储
- 用户数据源的 SQL 执行需要在沙箱中进行
- 沙盒服务需要通过 `make sandbox-start` 启动
