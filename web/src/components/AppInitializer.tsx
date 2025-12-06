import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useToast } from '@/hooks/use-toast';
import { setGlobalErrorHandler } from '@/lib/queryClient';
import { useAuthStore } from '@/stores/authStore';
import { useThemeStore } from '@/stores/themeStore';

interface AppInitializerProps {
  children: React.ReactNode;
}

/**
 * 应用初始化组件
 * 负责初始化主题、认证状态、全局错误处理等
 */
export const AppInitializer = ({ children }: AppInitializerProps) => {
  const [initialized, setInitialized] = useState(false);
  const initTheme = useThemeStore((state) => state.initTheme);
  const initAuth = useAuthStore((state) => state.initAuth);
  const { toast } = useToast();
  const { t } = useTranslation();

  useEffect(() => {
    // 设置全局 API 错误处理
    setGlobalErrorHandler((error) => {
      toast({
        title: t('common.error'),
        description: error.message,
        variant: 'destructive',
      });
    });

    // 初始化主题
    initTheme();
    // 初始化认证状态
    initAuth();
    // 标记初始化完成
    setInitialized(true);
  }, [initTheme, initAuth, toast, t]);

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">加载中...</div>
      </div>
    );
  }

  return <>{children}</>;
};
