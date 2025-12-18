# Fast Data Agent 前端

基于 React + TypeScript + Vite 构建的智能数据分析平台前端。

## 📱 功能页面

### 仪表盘 (Dashboard)
- 数据概览：数据源、会话、图表统计
- 快速操作：新建会话、添加数据源
- 最近会话列表

### 分析会话 (Sessions)
- 会话管理：创建、删除、归档
- 与 AI 对话分析数据
- 自然语言生成 SQL 查询和图表

### 数据源 (Data Sources)
- 数据库连接管理（MySQL/PostgreSQL）
- 文件上传（CSV/Excel/JSON/Parquet）
- 数据对象浏览和预览

### 图表工作台 (Charts) ✨
- **图表浏览**：展示所有会话中生成的可视化图表
- **搜索功能**：支持按标题、数据内容搜索
- **图表预览**：卡片缩略图 + 全屏查看
- **图表操作**：下载 PNG、跳转来源会话
- **统计信息**：总图表数、本周新增数

### 设置 (Settings)
- 个人信息管理
- 密码修改
- 外观设置（深色/浅色主题）

---

## 🎯 技术特性

### 核心技术栈
- **React 18** - 现代化的 UI 框架
- **TypeScript** - 类型安全
- **Vite** - 快速的构建工具
- **React Router** - 路由管理

### 数据获取与状态管理
- **TanStack Query** - 强大的数据获取和缓存库
- **Zustand** - 轻量级状态管理
- **Axios** - HTTP 客户端

### 表单处理
- **React Hook Form** - 高性能表单库
- **Zod** - TypeScript 优先的 Schema 验证
- **@hookform/resolvers** - 表单验证适配器

### UI 组件库
- **shadcn/ui** - 基于 Radix UI 的高质量组件
- **Tailwind CSS** - 实用优先的 CSS 框架
- **Lucide React** - 美观的图标库

### 测试框架
- **Vitest** - 快速的单元测试框架
- **@testing-library/react** - React 组件测试
- **jsdom** - 浏览器环境模拟

### 开发工具
- **Biome** - 快速的代码检查和格式化工具
- **Orval** - 自动生成 API 类型定义
- **pnpm** - 高效的包管理器

### 国际化
- **i18next** - 国际化框架
- **react-i18next** - React 集成

## 📁 项目结构

```
src/
├── api/                    # API 类型定义（自动生成）
├── components/             # 可复用组件
│   ├── ui/                 # shadcn/ui 组件
│   ├── FormExample.tsx     # 表单示例组件
│   └── index.ts            # 组件导出索引
├── hooks/                  # 自定义 Hooks
│   ├── useApi.ts           # TanStack Query 封装
│   ├── use-toast.ts        # Toast 通知
│   └── index.ts            # Hooks 导出索引
├── lib/                    # 库配置
│   ├── queryClient.ts      # TanStack Query 客户端
│   ├── validations.ts      # Zod 验证 Schema
│   └── utils.ts            # cn() 工具函数
├── pages/                  # 页面组件
├── stores/                 # Zustand 状态管理
├── test/                   # 测试配置
│   ├── setup.ts            # 测试初始化
│   └── utils.tsx           # 测试工具函数
├── utils/                  # 工具函数
│   ├── request.ts          # HTTP 请求封装
│   ├── storage.ts          # 本地存储工具
│   └── date.ts             # 日期格式化工具
├── App.tsx                 # 根组件
├── main.tsx                # 应用入口
├── i18n.ts                 # i18n 配置
└── index.css               # 全局样式
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pnpm install
```

### 2. 启动开发服务器

```bash
pnpm run dev
```

访问 http://localhost:5173

### 3. 构建生产版本

```bash
pnpm run build
```

## 🛠️ 可用脚本

```bash
# 开发
pnpm run dev              # 启动开发服务器
pnpm run build            # 构建生产版本
pnpm run preview          # 预览生产构建

# 代码质量
pnpm run check            # 检查并自动修复
pnpm run format           # 格式化代码
pnpm run lint             # 检查代码问题

# 测试
pnpm run test             # 运行测试（监听模式）
pnpm run test:run         # 运行测试（单次）
pnpm run test:coverage    # 运行测试并生成覆盖率报告

# API 类型生成
pnpm run gen:apis         # 生成 API 类型定义
```

## 📝 开发指南

### 表单处理（React Hook Form + Zod）

使用预定义的验证 Schema：

```tsx
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { type LoginFormData, loginSchema } from '@/lib/validations';

const {
  register,
  handleSubmit,
  formState: { errors, isSubmitting },
} = useForm<LoginFormData>({
  resolver: zodResolver(loginSchema),
});

const onSubmit = async (data: LoginFormData) => {
  // 处理提交
};

return (
  <form onSubmit={handleSubmit(onSubmit)}>
    <Input {...register('username')} />
    {errors.username && <p>{errors.username.message}</p>}
    <Button type="submit" disabled={isSubmitting}>
      {isSubmitting ? '提交中...' : '提交'}
    </Button>
  </form>
);
```

自定义验证 Schema：

```tsx
import { z } from 'zod';
import { emailSchema, passwordSchema } from '@/lib/validations';

const myFormSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  name: z.string().min(1, '名称不能为空'),
});

type MyFormData = z.infer<typeof myFormSchema>;
```

### 数据获取（TanStack Query）

```tsx
import { useApiQuery, useApiMutation } from '@/hooks/useApi';

// GET 请求
const { data, isLoading, error } = useApiQuery(['users'], '/api/users');

// POST/PUT/DELETE 请求
const mutation = useApiMutation('/api/users', 'post');
mutation.mutate({ name: 'John' });

// 带自动刷新
const mutation = useApiMutationWithRefresh('/api/users', 'post', [['users']]);
```

### 状态管理（Zustand）

```tsx
import { create } from 'zustand';

interface MyState {
  count: number;
  increment: () => void;
}

export const useMyStore = create<MyState>((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
}));

// 使用
const { count, increment } = useMyStore();
```

### 测试

编写测试：

```tsx
// src/components/MyComponent.test.tsx
import { render, screen } from '@/test/utils';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

运行测试：

```bash
pnpm run test:run
```

### 添加 UI 组件

```bash
npx shadcn@latest add button
npx shadcn@latest add dialog
npx shadcn@latest add input
```

## 📚 预定义验证 Schema

`src/lib/validations.ts` 包含常用的验证规则：

| Schema | 说明 |
|--------|------|
| `usernameSchema` | 用户名（3-20字符，字母数字下划线） |
| `emailSchema` | 邮箱格式验证 |
| `passwordSchema` | 密码（6-50字符） |
| `strongPasswordSchema` | 强密码（包含大小写、数字、特殊字符） |
| `phoneSchema` | 中国大陆手机号 |
| `urlSchema` | URL 格式验证 |
| `loginSchema` | 登录表单 |
| `registerSchema` | 注册表单 |
| `profileSchema` | 个人资料 |

## 🎨 样式指南

### Tailwind CSS

```tsx
<div className="flex items-center gap-4 p-4 bg-white rounded-lg shadow-md">
  <h1 className="text-2xl font-bold text-gray-900">Title</h1>
</div>
```

### 响应式设计

```tsx
<div className="w-full md:w-1/2 lg:w-1/3">
  {/* 移动端全宽，平板半宽，桌面1/3宽 */}
</div>
```

### 深色模式

主题切换已集成在 `useThemeStore` 中：

```tsx
import { useThemeStore } from '@/stores/themeStore';

const { theme, toggleTheme } = useThemeStore();
```

## 📄 许可证

MIT License
