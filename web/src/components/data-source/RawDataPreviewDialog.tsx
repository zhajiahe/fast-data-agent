import { Eye } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRawDataPreview } from '@/api';
import { DataTable } from '@/components/chat/DataTable';
import { LoadingSpinner } from '@/components/common';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface RawDataPreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rawDataId: string | null;
  rawDataName?: string;
}

/**
 * 单个数据对象（RawData）预览对话框
 */
export const RawDataPreviewDialog = ({ open, onOpenChange, rawDataId, rawDataName }: RawDataPreviewDialogProps) => {
  const { t } = useTranslation();

  const { data: response, isLoading, error } = useRawDataPreview(rawDataId || undefined, { limit: 100 });

  const preview = response?.data.data;
  const columns = preview?.columns || [];
  const rows = preview?.rows || [];

  const tableColumns = columns.map((col) => col.name);
  const tableRows = rows.map((row) => tableColumns.map((c) => row[c]));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            {rawDataName || t('dataSources.previewData')}
          </DialogTitle>
          <DialogDescription>
            {tableRows.length > 0 ? `${t('dataSources.previewData')} · ${tableRows.length} 行` : t('dataSources.previewData')}
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
            <div className="text-center py-12 text-muted-foreground">{t('common.noData') || '暂无数据'}</div>
          ) : (
            <DataTable columns={tableColumns} rows={tableRows} title={rawDataName || '数据预览'} pageSize={20} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

