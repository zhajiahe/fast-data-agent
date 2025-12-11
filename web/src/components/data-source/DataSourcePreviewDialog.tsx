import { Eye } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useDataSourcePreview } from '@/api';
import { DataTable } from '@/components/chat/DataTable';
import { LoadingSpinner } from '@/components/common';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface DataSourcePreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dataSourceId: number | null;
}

/**
 * 数据源预览对话框
 */
export const DataSourcePreviewDialog = ({ open, onOpenChange, dataSourceId }: DataSourcePreviewDialogProps) => {
  const { t } = useTranslation();

  const { data: response, isLoading, error } = useDataSourcePreview(dataSourceId || undefined, { limit: 100 });

  const preview = response?.data.data;

  // 将后端数据格式转换为 DataTable 需要的格式
  // columns 是 TargetField[]，需要提取 name 字段
  const columnDefs = preview?.columns || [];
  const rows = preview?.rows || [];

  // 转换为 DataTable 格式
  const tableColumns = columnDefs.map((col) => col.name);
  const tableRows = rows.map((row) => {
    return tableColumns.map((colName) => row[colName]);
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            {t('dataSources.previewData')}
          </DialogTitle>
          <DialogDescription>
            {tableRows.length > 0 ? `显示前 ${tableRows.length} 行数据` : '数据预览'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <div className="text-center py-12 text-destructive">
              {t('common.error')}: {error.message}
            </div>
          ) : tableRows.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">暂无数据</div>
          ) : (
            <DataTable columns={tableColumns} rows={tableRows} title="数据预览" pageSize={20} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
