import { Database, Eye } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useDataSourceDetail, useDataSourcePreview } from '@/api';
import { DataTable } from '@/components/chat/DataTable';
import { LoadingSpinner } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { RawDataPreviewDialog } from './RawDataPreviewDialog';

interface DataSourcePreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dataSourceId: string | null;
}

/**
 * 数据源预览对话框
 */
export const DataSourcePreviewDialog = ({ open, onOpenChange, dataSourceId }: DataSourcePreviewDialogProps) => {
  const { t } = useTranslation();
  const [rawPreviewId, setRawPreviewId] = useState<string | null>(null);
  const [rawPreviewName, setRawPreviewName] = useState<string | undefined>(undefined);

  const { data: response, isLoading, error } = useDataSourcePreview(dataSourceId || undefined, { limit: 100 });
  const { data: detailRes } = useDataSourceDetail(dataSourceId || undefined);

  const preview = response?.data.data;
  const rawMappings = detailRes?.data.data?.raw_mappings || [];

  // 将后端数据格式转换为 DataTable 需要的格式（合并视图）
  const columnDefs = preview?.columns || [];
  const rows = preview?.rows || [];

  const tableColumns = columnDefs.map((col) => col.name);
  const tableRows = rows.map((row) => tableColumns.map((colName) => row[colName]));

  const handleOpenRawPreview = (id: string, name?: string) => {
    setRawPreviewId(id);
    setRawPreviewName(name);
  };

  const hasRawMappings = useMemo(() => rawMappings.length > 0, [rawMappings]);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-5xl max-h-[85vh] flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              {t('dataSources.previewData')}
            </DialogTitle>
            <DialogDescription>
              {tableRows.length > 0 ? `显示前 ${tableRows.length} 行数据（合并视图）` : '数据预览'}
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-auto border rounded-lg">
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
              <DataTable columns={tableColumns} rows={tableRows} title="合并视图预览" pageSize={20} />
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Database className="h-4 w-4" />
              分表预览
            </div>
            {!hasRawMappings ? (
              <div className="text-sm text-muted-foreground">无可用数据对象</div>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
                {rawMappings.map((m: any) => (
                  <div
                    key={m.raw_data_id}
                    className="border rounded-lg px-3 py-2 flex items-center justify-between bg-muted/30"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{m.raw_data_name || m.raw_data_id}</p>
                      <p className="text-xs text-muted-foreground">ID: {m.raw_data_id}</p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => handleOpenRawPreview(m.raw_data_id, m.raw_data_name)}>
                      {t('dataSources.previewData')}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <RawDataPreviewDialog
        open={!!rawPreviewId}
        onOpenChange={(v) => {
          if (!v) {
            setRawPreviewId(null);
            setRawPreviewName(undefined);
          }
        }}
        rawDataId={rawPreviewId}
        rawDataName={rawPreviewName}
      />
    </>
  );
};
