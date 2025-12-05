import { ChevronDown, ChevronsUpDown, ChevronUp, Download } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface DataTableProps {
  columns: string[];
  rows: unknown[][];
  title?: string;
  maxRows?: number;
}

/**
 * 数据表格组件
 */
export const DataTable = ({ columns, rows, title, maxRows = 10 }: DataTableProps) => {
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [showAll, setShowAll] = useState(false);

  // 排序后的数据
  const sortedRows = useMemo(() => {
    if (sortColumn === null) return rows;

    return [...rows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      let comparison = 0;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      } else {
        comparison = String(aVal).localeCompare(String(bVal));
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [rows, sortColumn, sortDirection]);

  // 显示的行数
  const displayRows = showAll ? sortedRows : sortedRows.slice(0, maxRows);

  // 切换排序
  const handleSort = (columnIndex: number) => {
    if (sortColumn === columnIndex) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(columnIndex);
      setSortDirection('asc');
    }
  };

  // 下载 CSV
  const handleDownload = () => {
    const csvContent = [
      columns.join(','),
      ...rows.map((row) =>
        row
          .map((cell) => {
            const str = String(cell ?? '');
            return str.includes(',') || str.includes('"') ? `"${str.replace(/"/g, '""')}"` : str;
          })
          .join(',')
      ),
    ].join('\n');

    const blob = new Blob([`\ufeff${csvContent}`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title || 'data'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 格式化单元格值
  const formatCell = (value: unknown): string => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') {
      return value.toLocaleString();
    }
    return String(value);
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-b">
        <span className="text-sm font-medium">
          {title || '查询结果'} ({rows.length} 行)
        </span>
        <Button variant="ghost" size="sm" onClick={handleDownload}>
          <Download className="h-4 w-4 mr-1" />
          导出
        </Button>
      </div>

      {/* 表格 */}
      <ScrollArea className="max-h-[400px]">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-muted/80 backdrop-blur">
            <tr>
              {columns.map((col, index) => (
                <th
                  key={index}
                  className="px-4 py-2 text-left font-medium cursor-pointer hover:bg-muted transition-colors"
                  onClick={() => handleSort(index)}
                >
                  <div className="flex items-center gap-1">
                    <span className="truncate">{col}</span>
                    {sortColumn === index ? (
                      sortDirection === 'asc' ? (
                        <ChevronUp className="h-4 w-4 shrink-0" />
                      ) : (
                        <ChevronDown className="h-4 w-4 shrink-0" />
                      )
                    ) : (
                      <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-30" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, rowIndex) => (
              <tr key={rowIndex} className={cn('border-t', rowIndex % 2 === 0 ? 'bg-background' : 'bg-muted/30')}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="px-4 py-2 truncate max-w-[200px]">
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollArea>

      {/* 显示更多 */}
      {rows.length > maxRows && (
        <div className="px-4 py-2 border-t bg-muted/30 text-center">
          <Button variant="ghost" size="sm" onClick={() => setShowAll(!showAll)}>
            {showAll ? '收起' : `显示全部 ${rows.length} 行`}
          </Button>
        </div>
      )}
    </div>
  );
};
