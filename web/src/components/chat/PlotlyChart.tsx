import { Download, Maximize2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface PlotlyChartProps {
  chartJson: string;
  title?: string;
}

/**
 * Plotly 图表渲染组件
 */
export const PlotlyChart = ({ chartJson, title }: PlotlyChartProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const chartData = useMemo(() => {
    try {
      return JSON.parse(chartJson);
    } catch (e) {
      console.error('Failed to parse chart JSON:', e);
      return null;
    }
  }, [chartJson]);

  if (!chartData) {
    return <div className="p-4 bg-destructive/10 rounded-lg text-destructive text-sm">图表数据解析失败</div>;
  }

  const { data, layout } = chartData;

  // 基础配置
  const baseConfig = {
    displayModeBar: true,
    modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d'],
    displaylogo: false,
    responsive: true,
  };

  // 基础布局
  const baseLayout = {
    ...layout,
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      family: 'Inter, system-ui, sans-serif',
      color: 'currentColor',
    },
    margin: { t: 40, r: 20, b: 40, l: 50 },
  };

  // 下载图表
  const handleDownload = () => {
    // Plotly 内置了下载功能，这里可以触发
    const plotElement = document.querySelector('.js-plotly-plot');
    if (plotElement) {
      // @ts-expect-error
      window.Plotly?.downloadImage(plotElement, {
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
        {/* 工具栏 */}
        <div className="absolute top-2 right-2 z-10 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button variant="secondary" size="icon" className="h-7 w-7" onClick={() => setIsFullscreen(true)}>
            <Maximize2 className="h-3.5 w-3.5" />
          </Button>
          <Button variant="secondary" size="icon" className="h-7 w-7" onClick={handleDownload}>
            <Download className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* 图表 */}
        <Plot
          data={data}
          layout={{
            ...baseLayout,
            autosize: true,
            height: 350,
          }}
          config={baseConfig}
          className="w-full"
          useResizeHandler
        />
      </div>

      {/* 全屏对话框 */}
      <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] w-full h-full">
          <DialogHeader>
            <DialogTitle>{title || '图表'}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0">
            <Plot
              data={data}
              layout={{
                ...baseLayout,
                autosize: true,
              }}
              config={baseConfig}
              className="w-full h-full"
              useResizeHandler
              style={{ width: '100%', height: 'calc(90vh - 100px)' }}
            />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};
