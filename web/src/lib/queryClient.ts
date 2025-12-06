import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query';

/**
 * 全局错误处理函数
 * 用于处理 mutation 错误的 Toast 提示
 */
let globalErrorHandler: ((error: Error) => void) | null = null;

export const setGlobalErrorHandler = (handler: (error: Error) => void) => {
  globalErrorHandler = handler;
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 默认缓存时间 5 分钟
      staleTime: 5 * 60 * 1000,
      // 默认缓存保留时间 30 分钟
      gcTime: 30 * 60 * 1000,
      // 窗口聚焦时重新获取
      refetchOnWindowFocus: false,
      // 重连时重新获取
      refetchOnReconnect: true,
      // 重试次数
      retry: 1,
    },
    mutations: {
      // mutation 重试次数
      retry: 0,
    },
  },
  queryCache: new QueryCache({
    onError: (error) => {
      // Query 错误不自动 toast，由组件自行处理
      console.error('Query error:', error);
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      // 如果 mutation 配置了 onError，不再全局处理
      if (mutation.options.onError) {
        return;
      }
      // 调用全局错误处理器
      if (globalErrorHandler) {
        globalErrorHandler(error as Error);
      }
    },
  }),
});
