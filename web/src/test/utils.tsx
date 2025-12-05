import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type RenderOptions, render } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { BrowserRouter } from 'react-router-dom';

// 创建测试用的 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

interface WrapperProps {
  children: ReactNode;
}

// 测试包装器
const AllProviders = ({ children }: WrapperProps) => {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
};

// 自定义 render 函数
const customRender = (ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) =>
  render(ui, { wrapper: AllProviders, ...options });

// 重新导出所有 testing-library 工具
export * from '@testing-library/react';
export { customRender as render };
