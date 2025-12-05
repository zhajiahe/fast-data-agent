import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * 受保护的路由组件
 * 未登录用户将被重定向到登录页
 */
export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    // 保存当前路径，登录后重定向
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
