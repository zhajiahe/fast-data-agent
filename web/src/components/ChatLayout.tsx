import { Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

interface ChatLayoutProps {
  children: React.ReactNode;
}

/**
 * 聊天页面专用布局（简化的顶栏）
 */
export const ChatLayout = ({ children }: ChatLayoutProps) => {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* 简化的顶栏 */}
      <header className="h-14 border-b bg-background/95 backdrop-blur shrink-0">
        <div className="h-full flex items-center px-4">
          <Link to="/" className="flex items-center space-x-2">
            <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="font-semibold text-sm bg-gradient-to-r from-violet-600 to-purple-600 bg-clip-text text-transparent">
              Fast Data Agent
            </span>
          </Link>
        </div>
      </header>

      {/* 聊天内容 */}
      <main className="flex-1 min-h-0">{children}</main>
    </div>
  );
};

