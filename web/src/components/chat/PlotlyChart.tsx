import { Download, Maximize2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

declare global {
  interface Window {
    Plotly: {
      newPlot: (el: HTMLElement, data: unknown[], layout?: object, config?: object) => void;
      react: (el: HTMLElement, data: unknown[], layout?: object, config?: object) => void;
      downloadImage: (el: HTMLElement, options: object) => void;
    };
  }
}

interface PlotlyChartProps {
  chartJson: string;
  title?: string;
}

/**
 * Plotly 图表渲染组件 (CDN 版本)
 */
export const PlotlyChart = ({ chartJson, title }: PlotlyChartProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);
  const fullscreenChartRef = useRef<HTMLDivElement>(null);

  const chartData = useMemo(() => {
    try {
      return JSON.parse(chartJson);
    } catch (e) {
      console.error('Failed to parse chart JSON:', e);
      return null;
    }
  }, [chartJson]);

  const baseConfig = {
    displayModeBar: true,
    modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d'],
    displaylogo: false,
    responsive: true,
  };

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

  // 渲染主图表
  useEffect(() => {
    if (!chartRef.current || !chartData?.data || !window.Plotly) return;
    window.Plotly.react(chartRef.current, chartData.data, { ...baseLayout, autosize: true, height: 350 }, baseConfig);
  }, [chartData, baseLayout]);

  // 渲染全屏图表
  useEffect(() => {
    if (!fullscreenChartRef.current || !chartData?.data || !window.Plotly || !isFullscreen) return;
    window.Plotly.react(fullscreenChartRef.current, chartData.data, { ...baseLayout, autosize: true }, baseConfig);
  }, [chartData, baseLayout, isFullscreen]);

  if (!chartData) {
    return <div className="p-4 bg-destructive/10 rounded-lg text-destructive text-sm">图表数据解析失败</div>;
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
        <DialogContent className="max-w-[90vw] max-h-[90vh] w-full h-full">
          <DialogHeader>
            <DialogTitle>{title || '图表'}</DialogTitle>
          </DialogHeader>
          <div ref={fullscreenChartRef} className="flex-1 min-h-0" style={{ height: 'calc(90vh - 100px)' }} />
        </DialogContent>
      </Dialog>
    </>
  );
};
