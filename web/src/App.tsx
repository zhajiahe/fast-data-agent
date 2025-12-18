import { lazy, Suspense } from 'react';
import { Navigate, Outlet, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import { AppInitializer } from '@/components/AppInitializer';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Toaster } from '@/components/ui/toaster';

// 动态导入页面组件（代码拆分）
const Dashboard = lazy(() => import('@/pages/Dashboard').then((m) => ({ default: m.Dashboard })));
const DataSources = lazy(() => import('@/pages/DataSources').then((m) => ({ default: m.DataSources })));
const Sessions = lazy(() => import('@/pages/Sessions').then((m) => ({ default: m.Sessions })));
const Charts = lazy(() => import('@/pages/Charts').then((m) => ({ default: m.Charts })));
const Chat = lazy(() => import('@/pages/Chat').then((m) => ({ default: m.Chat })));
const Settings = lazy(() => import('@/pages/Settings').then((m) => ({ default: m.Settings })));
const Login = lazy(() => import('@/pages/Login').then((m) => ({ default: m.Login })));
const Register = lazy(() => import('@/pages/Register').then((m) => ({ default: m.Register })));

/**
 * 加载状态组件
 */
const LoadingFallback = () => (
  <div className="min-h-screen flex items-center justify-center bg-background">
    <div className="flex flex-col items-center gap-4">
      <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      <p className="text-muted-foreground animate-pulse">加载中...</p>
    </div>
  </div>
);

/**
 * 带导航栏的受保护布局（普通页面）
 */
const ProtectedLayout = () => (
  <ProtectedRoute>
    <Layout>
      <Outlet />
    </Layout>
  </ProtectedRoute>
);

/**
 * 带导航栏的受保护布局（全屏页面，如聊天）
 */
const ProtectedFullHeightLayout = () => (
  <ProtectedRoute>
    <Layout fullHeight>
      <Outlet />
    </Layout>
  </ProtectedRoute>
);

/**
 * 应用根组件
 */
function App() {
  // BASE_URL 末尾有斜杠（如 /web/），需要去掉以匹配 Router basename
  const basePath = (import.meta.env.VITE_BASE_PATH || import.meta.env.BASE_URL || '/').replace(/\/$/, '') || '/';

  return (
    <Router basename={basePath}>
      <AppInitializer>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            {/* 认证页面 - 无导航栏 */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* 受保护的页面 - 带导航栏 */}
            <Route element={<ProtectedLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="data-sources" element={<DataSources />} />
              <Route path="sessions" element={<Sessions />} />
              <Route path="charts" element={<Charts />} />
              <Route path="settings" element={<Settings />} />
            </Route>

            {/* 聊天页面 - 带导航栏，全屏高度 */}
            <Route element={<ProtectedFullHeightLayout />}>
              <Route path="chat/:id" element={<Chat />} />
            </Route>

            {/* 默认重定向 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
        <Toaster />
      </AppInitializer>
    </Router>
  );
}

export default App;
