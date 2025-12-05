# 快速参考手册

## 🚀 常用命令

```bash
pnpm run dev          # 启动开发服务器
pnpm run build        # 构建生产版本
pnpm run check        # 检查并自动修复格式和lint问题
pnpm run test:run     # 运行测试
pnpm run gen:apis     # 根据 OpenAPI 规范生成 API 客户端
```

## 📦 添加 UI 组件

```bash
npx shadcn@latest add [component]  # button, card, dialog, input, select, table, tabs, toast...
```

## 📝 表单处理 (React Hook Form + Zod)

```tsx
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { loginSchema, type LoginFormData } from '@/lib/validations';

const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginFormData>({
  resolver: zodResolver(loginSchema),
});

// 预定义 Schema: usernameSchema, emailSchema, passwordSchema, loginSchema, registerSchema, profileSchema
```

## 📊 数据获取 (TanStack Query)

```tsx
import { useApiQuery, useApiMutation, useApiMutationWithRefresh } from '@/hooks/useApi';

const { data, isLoading } = useApiQuery(['users'], '/api/users');
const mutation = useApiMutation('/api/users', 'post');
const mutationWithRefresh = useApiMutationWithRefresh('/api/users', 'post', [['users']]);
```

## 🗃️ 状态管理 (Zustand)

```tsx
import { create } from 'zustand';

export const useMyStore = create<State>((set) => ({
  count: 0,
  increment: () => set((s) => ({ count: s.count + 1 })),
}));
```

## 🌍 国际化 (i18next)

```tsx
import { useTranslation } from 'react-i18next';
const { t, i18n } = useTranslation();

t('common.save')                    // 使用翻译
i18n.changeLanguage('zh')           // 切换语言
// 翻译文件: public/locales/{en,zh}/translation.json
```

## 🧪 测试 (Vitest)

```tsx
import { render, screen } from '@/test/utils';

describe('MyComponent', () => {
  it('renders', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

## 🎨 主题切换

```tsx
import { useThemeStore } from '@/stores/themeStore';
const { theme, toggleTheme } = useThemeStore();
```

## 📁 项目结构

```
src/
├── components/ui/     # shadcn/ui 组件
├── hooks/useApi.ts    # TanStack Query 封装
├── lib/validations.ts # Zod 验证 Schema
├── stores/            # Zustand 状态
├── pages/             # 页面组件
└── test/              # 测试配置
```
