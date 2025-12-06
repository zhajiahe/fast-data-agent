import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
};

/**
 * 统一的加载指示器组件
 */
export const LoadingSpinner = ({ size = 'md', className }: LoadingSpinnerProps) => {
  return <Loader2 className={cn('animate-spin text-muted-foreground', sizeClasses[size], className)} />;
};

/**
 * 全屏加载状态
 */
export const LoadingState = ({ text }: { text?: string }) => {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <LoadingSpinner size="lg" />
      {text && <p className="text-sm text-muted-foreground mt-3">{text}</p>}
    </div>
  );
};
