import { Eye } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useFilePreview } from '@/api';
import { DataTable } from '@/components/chat/DataTable';
import { LoadingSpinner } from '@/components/common';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface DataPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fileId: number | null;
  dataSourceName: string;
}

/**
 * 数据预览对话框
 */
export const DataPreviewDialog = ({ open, onOpenChange, fileId, dataSourceName }: DataPreviewDialogProps) => {
  const { t } = useTranslation();

  const { data: response, isLoading, error } = useFilePreview(fileId || 0, { rows: 100 });

  const preview = response?.data.data;

  // 将后端数据格式转换为 DataTable 需要的格式
  const columns = preview?.columns?.map((col) => col.name as string) || [];
  const rows =
    preview?.data?.map((row) => {
      return columns.map((colName) => row[colName]);
    }) || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            {t('dataSources.previewData')}
          </DialogTitle>
          <DialogDescription>
            {dataSourceName} - {preview?.total_rows ? `共 ${preview.total_rows} 行` : ''}
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
          ) : rows.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">{t('common.noData')}</div>
          ) : (
            <DataTable columns={columns} rows={rows} title={dataSourceName} pageSize={20} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
