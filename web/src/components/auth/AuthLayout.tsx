import type { ReactNode } from 'react';

interface AuthLayoutProps {
  children: ReactNode;
  title: string;
  subtitle: string;
}

/**
 * 认证页面统一布局
 * 使用与主题协调的深色背景（基于 primary 色调）
 */
export const AuthLayout = ({ children, title, subtitle }: AuthLayoutProps) => {
  return (
    <div className="min-h-screen flex">
      {/* 左侧品牌区域 - 使用主题色系的深色 */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-slate-800 to-teal-950 p-12 flex-col justify-between relative overflow-hidden">
        {/* 背景装饰 - 使用主题 teal/cyan 色调 */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-10 left-10 w-64 h-64 border border-teal-600 rounded-full" />
          <div className="absolute top-20 left-20 w-64 h-64 border border-teal-700 rounded-full" />
          <div className="absolute bottom-20 right-20 w-80 h-80 border border-cyan-600 rounded-full" />
          <div className="absolute bottom-10 right-10 w-80 h-80 border border-cyan-700 rounded-full" />
          {/* 点阵装饰 */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_1px_1px,_rgba(20,184,166,0.15)_1px,_transparent_0)] bg-[size:40px_40px]" />
        </div>

        {/* Logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <img src={`${import.meta.env.BASE_URL}data_agent_logo.png`} alt="Logo" className="h-10 w-auto rounded-xl" />
            <span className="text-2xl font-bold text-white">Fast Data Agent</span>
          </div>
        </div>

        {/* 主要内容 */}
        <div className="relative z-10 space-y-6">
          <h1 className="text-4xl font-bold text-white">{title}</h1>
          <p className="text-lg text-slate-300 max-w-md">{subtitle}</p>

          {/* 特性列表 */}
          <div className="space-y-4 pt-4">
            <FeatureItem icon="🔍" text="自然语言查询数据" />
            <FeatureItem icon="📊" text="智能图表生成" />
            <FeatureItem icon="⚡" text="多数据源支持" />
          </div>
        </div>

        {/* 底部 */}
        <div className="relative z-10 text-slate-500 text-sm">© 2024 Fast Data Agent. All rights reserved.</div>
      </div>

      {/* 右侧表单区域 */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">{children}</div>
    </div>
  );
};

const FeatureItem = ({ icon, text }: { icon: string; text: string }) => (
  <div className="flex items-center gap-3 text-slate-300">
    <span className="text-xl">{icon}</span>
    <span>{text}</span>
  </div>
);
