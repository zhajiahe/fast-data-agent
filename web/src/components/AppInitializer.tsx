import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useThemeStore } from '@/stores/themeStore';

interface AppInitializerProps {
  children: React.ReactNode;
}

/**
 * 应用初始化组件
 * 负责初始化主题、认证状态等
 */
export const AppInitializer = ({ children }: AppInitializerProps) => {
  const [initialized, setInitialized] = useState(false);
  const initTheme = useThemeStore((state) => state.initTheme);
  const initAuth = useAuthStore((state) => state.initAuth);

  useEffect(() => {
    // 初始化主题
    initTheme();
    // 初始化认证状态
    initAuth();
    // 标记初始化完成
    setInitialized(true);
  }, [initTheme, initAuth]);

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse text-muted-foreground">加载中...</div>
      </div>
    );
  }

  return <>{children}</>;
};
