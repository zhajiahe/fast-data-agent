import { Download, Maximize2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

declare global {
  interface Window {
    Plotly: {
      newPlot: (el: HTMLElement, data: unknown[], layout?: object, config?: object) => void;
      react: (el: HTMLElement, data: unknown[], layout?: object, config?: object) => void;
      downloadImage: (el: HTMLElement, options: object) => void;
      Plots?: {
        resize: (el: HTMLElement) => void;
      };
    };
  }
}

const BASE_CONFIG = {
  displayModeBar: true,
  modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d'],
  displaylogo: false,
  responsive: true,
};

interface PlotlyChartProps {
  chartJson: string;
  title?: string;
}

/**
 * Plotly 图表渲染组件 (CDN 版本)
 */
export const PlotlyChart = ({ chartJson, title }: PlotlyChartProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [plotlyReady, setPlotlyReady] = useState(!!window.Plotly);
  const chartRef = useRef<HTMLDivElement>(null);
  const fullscreenChartRef = useRef<HTMLDivElement>(null);

  // 等待 Plotly 加载完成
  useEffect(() => {
    if (window.Plotly) return;
    const id = setInterval(() => {
      if (!window.Plotly) return;
      setPlotlyReady(true);
      clearInterval(id);
    }, 100);
    return () => clearInterval(id);
  }, []);

  const chartData = useMemo(() => {
    try {
      return JSON.parse(chartJson);
    } catch (e) {
      console.error('Failed to parse chart JSON:', e);
      return null;
    }
  }, [chartJson]);

  const baseLayout = useMemo(
    () => ({
      ...(chartData?.layout || {}),
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { family: 'Inter, system-ui, sans-serif', color: 'currentColor' },
      margin: { t: 40, r: 20, b: 40, l: 50 },
    }),
    [chartData?.layout],
  );

  const renderChart = useCallback(
    (target: HTMLDivElement | null, height?: number) => {
      if (!target || !chartData?.data || !plotlyReady) return;
      window.Plotly.react(
        target,
        chartData.data,
        { ...baseLayout, autosize: true, ...(height ? { height } : {}) },
        BASE_CONFIG,
      );
    },
    [baseLayout, chartData?.data, plotlyReady],
  );

  // 渲染主图表
  useEffect(() => {
    renderChart(chartRef.current, 350);
  }, [renderChart]);

  // 渲染全屏图表
  useEffect(() => {
    if (!isFullscreen) return;
    // Dialog 打开时等待容器获得尺寸再渲染，避免宽高为 0 导致空白
    let cancelled = false;
    const renderFullscreen = () => {
      if (cancelled) return;
      const el = fullscreenChartRef.current;
      if (!el) {
        window.requestAnimationFrame(renderFullscreen);
        return;
      }
      const rect = el.getBoundingClientRect();
      if (!rect.width || !rect.height) {
        window.requestAnimationFrame(renderFullscreen);
        return;
      }
      renderChart(el, rect.height);
      window.Plotly.Plots?.resize(el);
    };

    renderFullscreen();

    const handleResize = () => {
      if (!fullscreenChartRef.current) return;
      window.Plotly.Plots?.resize(fullscreenChartRef.current);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      cancelled = true;
      window.removeEventListener('resize', handleResize);
    };
  }, [isFullscreen, renderChart]);

  if (!chartData) {
    return <div className="p-4 bg-destructive/10 rounded-lg text-destructive text-sm">图表数据解析失败</div>;
  }

  if (!plotlyReady) {
    return (
      <div className="flex items-center justify-center h-[350px] bg-muted/50 rounded-lg">
        <div className="text-muted-foreground text-sm">加载图表组件...</div>
      </div>
    );
  }

  const handleDownload = () => {
    if (chartRef.current && window.Plotly) {
      window.Plotly.downloadImage(chartRef.current, {
        format: 'png',
        width: 1200,
        height: 800,
        filename: title || 'chart',
      });
    }
  };

  return (
    <>
      <div className="relative group bg-card border rounded-lg overflow-hidden">
        <div className="absolute top-2 right-2 z-10 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button variant="secondary" size="icon" className="h-7 w-7" onClick={() => setIsFullscreen(true)}>
            <Maximize2 className="h-3.5 w-3.5" />
          </Button>
          <Button variant="secondary" size="icon" className="h-7 w-7" onClick={handleDownload}>
            <Download className="h-3.5 w-3.5" />
          </Button>
        </div>
        <div ref={chartRef} className="w-full" style={{ height: 350 }} />
      </div>

      <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
        <DialogContent aria-describedby={undefined} className="max-w-[90vw] max-h-[90vh] w-full h-full">
          <DialogHeader>
            <DialogTitle>{title || '图表'}</DialogTitle>
          </DialogHeader>
          <div
            ref={fullscreenChartRef}
            className="flex-1 min-h-0 w-full"
            style={{ height: 'calc(90vh - 100px)' }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};
