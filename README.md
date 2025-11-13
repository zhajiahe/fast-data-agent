# FastAPI后端开发实践（0-1）
> 友情提示：本文含大量AI生成内容
[https://github.com/zhajiahe/fastapi-template](项目地址)
## 基础概念

### 核心依赖
FastAPI 构建在以下优秀的库之上：

- **Starlette**：负责 Web 部分
- **Pydantic**：负责数据部分，提供数据验证和设置管理
- **Uvicorn**：ASGI 服务器，用于运行应用

### 建议的依赖
- **uv**: 极快的Python包管理器
- **SQLAlchemy**: 数据库ORM，支持异步操作
- **Alembic**: 数据库迁移工具，类似数据库的Git
- **Loguru**: 增强的日志工具
- **Pre-commit**: Git提交前自动检查代码质量
- **Ruff**: 快速的Python代码检查和格式化工具
- **MyPy**: Python静态类型检查器
- **Bcrypt**: 现代化密码加密库
- **Python-JOSE**: JWT令牌处理

## 项目模板

下面的模板结合异步FastAPI最佳实践，集成数据库迁移、测试、代码检查、类型检查为一体，是推荐的FastAPI项目初始化最佳模板。基于该模板可以进一步增加功能，实现真正的后端服务。

## 项目结构

```
fastapi-template/
├── app/                      # 应用核心代码
│   ├── api/                  # API路由
│   │   └── users.py          # 用户相关API
│   ├── core/                 # 核心配置模块
│   │   ├── config.py         # 配置管理
│   │   ├── database.py       # 数据库连接
│   │   ├── deps.py           # 依赖注入
│   │   ├── lifespan.py       # 应用生命周期
│   │   └── security.py       # 安全认证
│   ├── middleware/           # 中间件
│   │   └── logging.py        # 日志中间件
│   ├── models/               # 数据库模型
│   │   ├── base.py           # 基础模型和响应类
│   │   └── user.py           # 用户模型
│   ├── schemas/              # Pydantic模型
│   │   └── user.py           # 用户Schema
│   ├── utils/                # 工具函数
│   └── main.py               # 应用入口
├── alembic/                  # 数据库迁移
│   ├── versions/             # 迁移脚本
│   └── env.py                # Alembic配置
├── scripts/                  # 脚本工具
│   ├── create_superuser.py   # 创建超级管理员
│   └── init_db.py            # 初始化数据库
├── tests/                    # 测试代码
│   ├── integration/          # 集成测试
│   └── conftest.py           # 测试配置
├── logs/                     # 日志目录
├── .env                      # 环境变量（需自行创建）
├── .gitignore               # Git忽略文件
├── alembic.ini              # Alembic配置
├── Makefile                 # Make命令集合
├── pyproject.toml           # 项目配置和依赖
└── README.md                # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
# 安装uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目并安装依赖
git clone <your-repo-url>
cd fastapi-template
uv sync
```

### 2. 配置环境变量

创建 `.env` 文件并配置：

```bash
# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./test.db

# JWT配置（生产环境务必修改）
SECRET_KEY=your-secret-key-change-in-production
REFRESH_SECRET_KEY=your-refresh-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 应用配置
APP_NAME=FastAPI-Template
DEBUG=true
```

### 3. 初始化数据库

```bash
# 使用Makefile命令
make db-upgrade

# 或直接使用Python脚本
uv run python scripts/init_db.py
```

### 4. 创建超级管理员

```bash
uv run python scripts/create_superuser.py
```

### 5. 启动开发服务器

```bash
# 使用Makefile
make dev

# 或直接使用uvicorn
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看API文档

## 核心功能

### 1. 用户认证系统

- ✅ 用户注册与登录
- ✅ JWT令牌认证（Access Token + Refresh Token）
- ✅ 密码加密（Bcrypt）
- ✅ 用户权限管理（普通用户/超级管理员）
- ✅ 当前用户信息获取
- ✅ 密码修改

### 2. 用户管理（需超级管理员权限）

- ✅ 用户CRUD操作
- ✅ 分页查询
- ✅ 关键词搜索（用户名/邮箱/昵称）
- ✅ 状态过滤（激活状态/管理员权限）
- ✅ 逻辑删除

### 3. 数据库特性

- ✅ SQLAlchemy 2.0+ 异步ORM
- ✅ Alembic数据库迁移
- ✅ 通用基础模型（包含ID、创建时间、更新时间、逻辑删除）
- ✅ 连接池管理
- ✅ 自动事务管理

### 4. 代码质量保证

- ✅ Ruff代码检查和格式化
- ✅ MyPy类型检查
- ✅ Pytest单元测试和集成测试
- ✅ 测试覆盖率支持
- ✅ Pre-commit钩子

### 5. 日志系统

- ✅ Loguru结构化日志
- ✅ 请求日志中间件
- ✅ 日志文件自动轮转
- ✅ 错误日志单独记录
- ✅ 控制台彩色输出

## 常用命令

项目使用 Makefile 简化常用操作：

```bash
make help          # 显示帮助信息
make install       # 安装依赖
make dev           # 启动开发服务器
make test          # 运行测试
make lint          # 代码检查
make lint-fix      # 代码检查并自动修复
make format        # 格式化代码
make type-check    # 类型检查
make db-migrate msg="描述"  # 创建数据库迁移
make db-upgrade    # 升级数据库
make db-downgrade  # 降级数据库
make clean         # 清理临时文件
```

**Happy Coding! 🚀**
