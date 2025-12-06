import { ChevronDown, ChevronLeft, ChevronRight, ChevronsUpDown, ChevronUp, Download } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DataTableProps {
  columns: string[];
  rows: unknown[][];
  title?: string;
  pageSize?: number;
}

/**
 * 数据表格组件（支持分页）
 */
export const DataTable = ({ columns, rows, title, pageSize = 10 }: DataTableProps) => {
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);

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

  // 分页计算
  const totalPages = Math.ceil(sortedRows.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const displayRows = sortedRows.slice(startIndex, startIndex + pageSize);

  // 切换排序（排序后重置到第一页）
  const handleSort = (columnIndex: number) => {
    if (sortColumn === columnIndex) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(columnIndex);
      setSortDirection('asc');
    }
    setCurrentPage(1);
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
    <div className="border rounded-md overflow-hidden text-xs">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-2 py-1 bg-muted/50 border-b">
        <span className="font-medium">
          {title || '查询结果'} ({rows.length} 行)
        </span>
        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={handleDownload}>
          <Download className="h-3 w-3 mr-1" />
          导出
        </Button>
      </div>

      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-muted/60">
            <tr>
              {columns.map((col, index) => (
                <th
                  key={col}
                  className="px-2 py-1.5 text-left font-medium cursor-pointer hover:bg-muted transition-colors"
                  onClick={() => handleSort(index)}
                >
                  <div className="flex items-center gap-0.5">
                    <span className="truncate">{col}</span>
                    {sortColumn === index ? (
                      sortDirection === 'asc' ? (
                        <ChevronUp className="h-3 w-3 shrink-0" />
                      ) : (
                        <ChevronDown className="h-3 w-3 shrink-0" />
                      )
                    ) : (
                      <ChevronsUpDown className="h-3 w-3 shrink-0 opacity-30" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, rowIndex) => (
              <tr
                key={`row-${startIndex + rowIndex}`}
                className={cn('border-t', rowIndex % 2 === 0 ? 'bg-background' : 'bg-muted/20')}
              >
                {row.map((cell, cellIndex) => (
                  <td key={`cell-${startIndex + rowIndex}-${cellIndex}`} className="px-2 py-1 truncate max-w-[180px]">
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页控件 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-2 py-1 border-t bg-muted/30">
          <span className="text-muted-foreground">
            {startIndex + 1}-{Math.min(startIndex + pageSize, rows.length)} / {rows.length}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage((p) => p - 1)}
            >
              <ChevronLeft className="h-3 w-3" />
            </Button>
            <span className="px-2 text-muted-foreground">
              {currentPage} / {totalPages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage((p) => p + 1)}
            >
              <ChevronRight className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
