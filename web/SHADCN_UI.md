# shadcn/ui 组件库使用指南

本项目已集成 shadcn/ui 组件库，提供了丰富的、可定制的 React 组件。

## 📦 已安装的组件

以下组件已经安装并可以直接使用：

- **Button** - 按钮组件
- **Card** - 卡片组件
- **Input** - 输入框组件
- **Textarea** - 文本域组件
- **Label** - 标签组件
- **Dialog** - 对话框组件
- **Select** - 选择器组件
- **Dropdown Menu** - 下拉菜单组件
- **Separator** - 分隔线组件
- **Avatar** - 头像组件
- **Badge** - 徽章组件
- **Toast** - 通知组件
- **Sheet** - 侧边栏组件
- **Scroll Area** - 滚动区域组件

## 🚀 快速开始

### 导入组件

```tsx
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useToast } from "@/hooks/use-toast"
```

### 使用示例

#### Button 组件

```tsx
import { Button } from "@/components/ui/button"

function MyComponent() {
  return (
    <div className="flex gap-2">
      <Button>默认按钮</Button>
      <Button variant="destructive">危险按钮</Button>
      <Button variant="outline">轮廓按钮</Button>
      <Button variant="ghost">幽灵按钮</Button>
      <Button variant="secondary">次要按钮</Button>
      <Button size="sm">小按钮</Button>
      <Button size="lg">大按钮</Button>
    </div>
  )
}
```

#### Card 组件

```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"

function MyCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>卡片标题</CardTitle>
        <CardDescription>卡片描述</CardDescription>
      </CardHeader>
      <CardContent>
        <p>卡片内容</p>
      </CardContent>
    </Card>
  )
}
```

#### Toast 通知

```tsx
import { useToast } from "@/hooks/use-toast"
import { Button } from "@/components/ui/button"

function MyComponent() {
  const { toast } = useToast()

  return (
    <Button
      onClick={() => {
        toast({
          title: "通知标题",
          description: "这是一条通知消息",
        })
      }}
    >
      显示通知
    </Button>
  )
}
```

#### Dialog 对话框

```tsx
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

function MyDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>打开对话框</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>对话框标题</DialogTitle>
          <DialogDescription>对话框描述</DialogDescription>
        </DialogHeader>
        <p>对话框内容</p>
      </DialogContent>
    </Dialog>
  )
}
```

## 🎨 主题定制

项目使用 CSS 变量来管理主题颜色，支持亮色和暗色模式。

### 颜色变量

所有颜色都在 `src/index.css` 中定义：

- `--background` - 背景色
- `--foreground` - 前景色（文本）
- `--primary` - 主色
- `--secondary` - 次要色
- `--muted` - 静音色
- `--accent` - 强调色
- `--destructive` - 危险色
- `--border` - 边框色
- `--input` - 输入框背景色
- `--ring` - 焦点环颜色

### 切换暗色模式

在 HTML 根元素上添加 `dark` 类即可启用暗色模式：

```tsx
// 切换暗色模式
document.documentElement.classList.toggle('dark')
```

## 📚 添加新组件

使用 shadcn CLI 添加新组件：

```bash
npx shadcn@latest add [component-name]
```

例如：

```bash
npx shadcn@latest add table
npx shadcn@latest add tabs
npx shadcn@latest add form
```

## 🔗 参考资源

- [shadcn/ui 官方文档](https://ui.shadcn.com/)
- [组件列表](https://ui.shadcn.com/docs/components)
- [主题定制](https://ui.shadcn.com/docs/theming)

## 💡 最佳实践

1. **使用 cn() 工具函数**：合并 Tailwind 类名时使用 `cn()` 函数
2. **组件组合**：shadcn/ui 组件设计为可组合的，可以灵活组合使用
3. **类型安全**：所有组件都有完整的 TypeScript 类型定义
4. **无障碍性**：组件基于 Radix UI 构建，具有良好的无障碍性支持
