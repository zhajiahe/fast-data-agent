import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileSpreadsheet,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { type DataSourceResponse, useDataSources, useDeleteDataSource, useSyncDataSourceSchema } from '@/api';
import { AddDatabaseDialog } from '@/components/data-source/AddDatabaseDialog';
import { UploadFileDialog } from '@/components/data-source/UploadFileDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useConfirmDialog, useToast } from '@/hooks';

/**
 * 数据源管理页面
 */
export const DataSources = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [showAddDatabase, setShowAddDatabase] = useState(false);
  const [showUploadFile, setShowUploadFile] = useState(false);
  const { confirm, ConfirmDialog } = useConfirmDialog();

  // 使用生成的 API hooks
  const { data: response, isLoading, refetch } = useDataSources();
  const deleteDataSourceMutation = useDeleteDataSource();
  const syncSchemaMutation = useSyncDataSourceSchema();

  const dataSources = response?.data.data?.items || [];

  const handleDelete = async (id: number, name: string) => {
    const confirmed = await confirm({
      title: t('dataSources.confirmDeleteTitle'),
      description: t('dataSources.confirmDelete', { name }),
      confirmText: t('common.delete'),
      cancelText: t('common.cancel'),
      variant: 'destructive',
    });

    if (!confirmed) return;

    deleteDataSourceMutation.mutate(id, {
      onSuccess: () => {
        toast({ title: t('common.success'), description: t('dataSources.deleteSuccess') });
      },
      // 错误由全局处理器处理
    });
  };

  const handleSyncSchema = async (id: number) => {
    syncSchemaMutation.mutate(id, {
      onSuccess: () => {
        toast({ title: t('common.success'), description: 'Schema 同步成功' });
      },
    });
  };

  const getTypeIcon = (ds: DataSourceResponse) => {
    if (ds.source_type === 'database') {
      return <Database className="h-5 w-5 text-blue-500" />;
    }
    return <FileSpreadsheet className="h-5 w-5 text-green-500" />;
  };

  const getStatusBadge = (_ds: DataSourceResponse) => {
    // 暂时认为所有数据源都是活跃的
    const isActive = true;
    if (isActive) {
      return (
        <Badge variant="outline" className="text-green-600 border-green-300 bg-green-50">
          <CheckCircle2 className="h-3 w-3 mr-1" />
          {t('dataSources.active')}
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="text-red-600 border-red-300 bg-red-50">
        <AlertCircle className="h-3 w-3 mr-1" />
        {t('dataSources.inactive')}
      </Badge>
    );
  };

  return (
    <div className="container py-8 max-w-6xl">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('dataSources.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('dataSources.subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('common.refresh')}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                {t('dataSources.add')}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setShowAddDatabase(true)}>
                <Database className="h-4 w-4 mr-2" />
                {t('dataSources.addDatabase')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShowUploadFile(true)}>
                <Upload className="h-4 w-4 mr-2" />
                {t('dataSources.uploadFile')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* 数据源列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : dataSources.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">{t('dataSources.empty')}</h3>
            <p className="text-muted-foreground text-center mb-4">{t('dataSources.emptyHint')}</p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowAddDatabase(true)}>
                <Database className="h-4 w-4 mr-2" />
                {t('dataSources.addDatabase')}
              </Button>
              <Button variant="outline" onClick={() => setShowUploadFile(true)}>
                <Upload className="h-4 w-4 mr-2" />
                {t('dataSources.uploadFile')}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {dataSources.map((ds) => (
            <Card key={ds.id} className="group hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {getTypeIcon(ds)}
                    <div>
                      <CardTitle className="text-base">{ds.name}</CardTitle>
                      <CardDescription className="text-xs">
                        {ds.source_type === 'database' ? ds.db_type?.toUpperCase() : t('dataSources.file')}
                      </CardDescription>
                    </div>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleSyncSchema(ds.id)}>
                        <RefreshCw className="h-4 w-4 mr-2" />
                        {t('dataSources.refreshSchema')}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className="text-destructive" onClick={() => handleDelete(ds.id, ds.name)}>
                        <Trash2 className="h-4 w-4 mr-2" />
                        {t('common.delete')}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  {getStatusBadge(ds)}
                  {ds.create_time && (
                    <span className="text-xs text-muted-foreground">
                      {new Date(ds.create_time).toLocaleDateString()}
                    </span>
                  )}
                </div>
                {ds.description && <p className="text-sm text-muted-foreground mt-3 line-clamp-2">{ds.description}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 对话框 */}
      <AddDatabaseDialog open={showAddDatabase} onOpenChange={setShowAddDatabase} />
      <UploadFileDialog open={showUploadFile} onOpenChange={setShowUploadFile} />

      {/* 确认对话框 */}
      <ConfirmDialog />
    </div>
  );
};
