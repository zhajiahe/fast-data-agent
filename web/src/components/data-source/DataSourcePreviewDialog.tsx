import { Database, Eye, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useDataSourceDetail, useRawDataPreview } from '@/api';
import { DataTable } from '@/components/chat/DataTable';
import { LoadingSpinner } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface DataSourcePreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dataSourceId: string | null;
}

/**
 * 数据源预览（分表 Tab，内嵌显示，不再使用弹窗合并视图）
 */
export const DataSourcePreviewDialog = ({ open, onOpenChange, dataSourceId }: DataSourcePreviewDialogProps) => {
  const { t } = useTranslation();
  const [activeRawId, setActiveRawId] = useState<string | undefined>(undefined);

  const { data: detailRes } = useDataSourceDetail(dataSourceId || undefined);
  const rawMappings = detailRes?.data.data?.raw_mappings || [];
  const hasRawMappings = useMemo(() => rawMappings.length > 0, [rawMappings]);

  useEffect(() => {
    if (open && rawMappings.length > 0) {
      setActiveRawId((prev) => prev || rawMappings[0].raw_data_id);
    }
    if (!open) {
      setActiveRawId(undefined);
    }
  }, [open, rawMappings]);

  const { data: previewRes, isLoading, error } = useRawDataPreview(activeRawId, { limit: 100 });
  const preview = previewRes?.data.data;
  const columns = preview?.columns || [];
  const rows = preview?.rows || [];
  const tableColumns = columns.map((c: any) => c.name);
  const tableRows = rows.map((r: any) => tableColumns.map((c) => r[c]));

  if (!open) return null;

  return (
    <Card className="mt-4">
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Eye className="h-5 w-5" />
          <CardTitle>{t('dataSources.previewData')}</CardTitle>
          <span className="text-sm text-muted-foreground">(分表预览)</span>
        </div>
        <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}>
          <X className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {!hasRawMappings ? (
          <div className="text-sm text-muted-foreground">无可用数据对象</div>
        ) : (
          <Tabs value={activeRawId} onValueChange={(v) => setActiveRawId(v)}>
            <TabsList className="w-full overflow-auto">
              {rawMappings.map((m: any) => (
                <TabsTrigger key={m.raw_data_id} value={m.raw_data_id} className="whitespace-nowrap">
                  <Database className="h-4 w-4 mr-2" />
                  {m.raw_data_name || m.raw_data_id}
                </TabsTrigger>
              ))}
            </TabsList>
            {rawMappings.map((m: any) => (
              <TabsContent key={m.raw_data_id} value={m.raw_data_id} className="mt-4">
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
                  <DataTable
                    columns={tableColumns}
                    rows={tableRows}
                    title={m.raw_data_name || '数据预览'}
                    pageSize={20}
                  />
                )}
              </TabsContent>
            ))}
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
};
