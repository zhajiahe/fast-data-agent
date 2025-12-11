import {
  Database,
  FileSpreadsheet,
  HardDrive,
  Layers,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Table2,
  Trash2,
  Upload,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  useDataSources,
  useDbConnections,
  useDeleteDataSource,
  useDeleteDbConnection,
  useDeleteFile,
  useFiles,
  useRawDataList,
  useSyncDataSourceSchema,
} from '@/api';
import { EmptyState } from '@/components/common';
import { AddDatabaseDialog } from '@/components/data-source/AddDatabaseDialog';
import { CreateDataSourceDialog } from '@/components/data-source/CreateDataSourceDialog';
import { DataSourcePreviewDialog } from '@/components/data-source/DataSourcePreviewDialog';
import { UploadFileDialog } from '@/components/data-source/UploadFileDialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';

// 辅助函数：格式化文件大小
const formatFileSize = (bytes: number | null | undefined): string => {
  if (!bytes) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

// 辅助函数：格式化日期
const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * 数据源管理页面
 *
 * 整合数据库连接、文件上传、数据对象、数据源管理
 */
export const DataSources = () => {
  const { t } = useTranslation();
  const { toast } = useToast();

  // 对话框状态
  const [showCreateDataSourceDialog, setShowCreateDataSourceDialog] = useState(false);
  const [showAddDbDialog, setShowAddDbDialog] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [previewDataSourceId, setPreviewDataSourceId] = useState<number | null>(null);

  // 删除确认状态
  const [deleteTarget, setDeleteTarget] = useState<{
    type: 'dataSource' | 'connection' | 'file';
    id: number;
    name: string;
  } | null>(null);

  // API Hooks
  const { data: dataSourcesRes, isLoading: dsLoading, refetch: refetchDs } = useDataSources({ page_size: 100 });
  const { data: connectionsRes, isLoading: connLoading, refetch: refetchConn } = useDbConnections({ page_size: 100 });
  const { data: filesRes, isLoading: filesLoading, refetch: refetchFiles } = useFiles();
  const { data: rawDataRes, isLoading: rawLoading, refetch: refetchRaw } = useRawDataList({ page_size: 100 });

  const deleteDataSourceMutation = useDeleteDataSource();
  const deleteConnectionMutation = useDeleteDbConnection();
  const deleteFileMutation = useDeleteFile();
  const syncSchemaMutation = useSyncDataSourceSchema();

  // 数据提取
  const dataSources = dataSourcesRes?.data.data?.items || [];
  const connections = connectionsRes?.data.data?.items || [];
  const files = filesRes?.data.data?.items || [];
  const rawDataList = rawDataRes?.data.data?.items || [];

  // 统计数据
  const stats = [
    {
      label: '数据源',
      value: dataSources.length,
      icon: Layers,
      color: 'text-teal-600 dark:text-teal-400',
      bgColor: 'bg-teal-500/10',
    },
    {
      label: '数据库连接',
      value: connections.length,
      icon: Database,
      color: 'text-slate-600 dark:text-slate-400',
      bgColor: 'bg-slate-500/10',
    },
    {
      label: '已上传文件',
      value: files.length,
      icon: FileSpreadsheet,
      color: 'text-emerald-600 dark:text-emerald-400',
      bgColor: 'bg-emerald-500/10',
    },
    {
      label: '数据对象',
      value: rawDataList.length,
      icon: HardDrive,
      color: 'text-cyan-600 dark:text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
  ];

  // 刷新所有数据
  const handleRefreshAll = () => {
    refetchDs();
    refetchConn();
    refetchFiles();
    refetchRaw();
    toast({ title: t('common.success'), description: '数据已刷新' });
  };

  // 处理删除
  const handleDelete = async () => {
    if (!deleteTarget) return;

    try {
      if (deleteTarget.type === 'dataSource') {
        await deleteDataSourceMutation.mutateAsync(deleteTarget.id);
      } else if (deleteTarget.type === 'connection') {
        await deleteConnectionMutation.mutateAsync(deleteTarget.id);
      } else if (deleteTarget.type === 'file') {
        await deleteFileMutation.mutateAsync(deleteTarget.id);
      }
      toast({ title: t('common.success'), description: `${deleteTarget.name} 已删除` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '删除失败';
      toast({ title: t('common.error'), description: msg, variant: 'destructive' });
    } finally {
      setDeleteTarget(null);
    }
  };

  // 刷新数据源 Schema
  const handleSyncSchema = async (id: number) => {
    try {
      await syncSchemaMutation.mutateAsync(id);
      toast({ title: t('common.success'), description: 'Schema 已刷新' });
    } catch {
      toast({ title: t('common.error'), description: '刷新失败', variant: 'destructive' });
    }
  };

  return (
    <div className="container py-8 max-w-6xl">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('dataSources.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('dataSources.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefreshAll}>
            <RefreshCw className="h-4 w-4 mr-2" />
            {t('common.refresh')}
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                {t('dataSources.add')}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setShowCreateDataSourceDialog(true)}>
                <Layers className="h-4 w-4 mr-2" />
                创建数据源
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShowAddDbDialog(true)}>
                <Database className="h-4 w-4 mr-2" />
                {t('dataSources.addDatabase')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShowUploadDialog(true)}>
                <Upload className="h-4 w-4 mr-2" />
                {t('dataSources.uploadFile')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {stats.map((stat) => (
          <Card key={stat.label} className="p-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold">{stat.value}</p>
                <p className="text-xs text-muted-foreground">{stat.label}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* 主内容区 - Tab 布局 */}
      <Tabs defaultValue="data-sources" className="space-y-4">
        <TabsList>
          <TabsTrigger value="data-sources" className="gap-2">
            <Layers className="h-4 w-4" />
            数据源
          </TabsTrigger>
          <TabsTrigger value="connections" className="gap-2">
            <Database className="h-4 w-4" />
            数据库连接
          </TabsTrigger>
          <TabsTrigger value="files" className="gap-2">
            <FileSpreadsheet className="h-4 w-4" />
            已上传文件
          </TabsTrigger>
          <TabsTrigger value="raw-data" className="gap-2">
            <HardDrive className="h-4 w-4" />
            数据对象
          </TabsTrigger>
        </TabsList>

        {/* 数据源 Tab */}
        <TabsContent value="data-sources">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-5 w-5" />
                数据源列表
              </CardTitle>
              <CardDescription>可用于分析会话的数据源，支持字段映射和数据预览</CardDescription>
            </CardHeader>
            <CardContent>
              {dsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : dataSources.length === 0 ? (
                <EmptyState
                  icon={Layers}
                  title={t('dataSources.empty')}
                  description="先添加数据对象（连接数据库或上传文件），然后创建数据源"
                  action={
                    <div className="flex flex-col gap-2">
                      {rawDataList.length > 0 ? (
                        <Button onClick={() => setShowCreateDataSourceDialog(true)}>
                          <Layers className="h-4 w-4 mr-2" />
                          创建数据源
                        </Button>
                      ) : (
                        <div className="flex gap-2">
                          <Button variant="outline" onClick={() => setShowAddDbDialog(true)}>
                            <Database className="h-4 w-4 mr-2" />
                            {t('dataSources.addDatabase')}
                          </Button>
                          <Button onClick={() => setShowUploadDialog(true)}>
                            <Upload className="h-4 w-4 mr-2" />
                            {t('dataSources.uploadFile')}
                          </Button>
                        </div>
                      )}
                    </div>
                  }
                />
              ) : (
                <div className="divide-y">
                  {dataSources.map((ds) => (
                    <div key={ds.id} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                      <div className="flex items-center gap-4">
                        <div className="p-2 rounded-lg bg-teal-500/10">
                          <Table2 className="h-5 w-5 text-teal-600 dark:text-teal-400" />
                        </div>
                        <div>
                          <p className="font-medium">{ds.name}</p>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>{ds.category || '数据源'}</span>
                            {ds.target_fields && ds.target_fields.length > 0 && (
                              <Badge variant="secondary" className="text-xs">
                                {ds.target_fields.length} 字段
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setPreviewDataSourceId(ds.id)}>
                          {t('dataSources.previewData')}
                        </Button>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleSyncSchema(ds.id)}>
                              <RefreshCw className="h-4 w-4 mr-2" />
                              {t('dataSources.refreshSchema')}
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setDeleteTarget({ type: 'dataSource', id: ds.id, name: ds.name })}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t('common.delete')}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 数据库连接 Tab */}
        <TabsContent value="connections">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  数据库连接
                </CardTitle>
                <CardDescription>管理外部数据库连接，连接后自动发现表并创建数据对象</CardDescription>
              </div>
              <Button onClick={() => setShowAddDbDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                添加连接
              </Button>
            </CardHeader>
            <CardContent>
              {connLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : connections.length === 0 ? (
                <EmptyState
                  icon={Database}
                  title="暂无数据库连接"
                  description="添加数据库连接以接入外部数据"
                  action={
                    <Button onClick={() => setShowAddDbDialog(true)}>
                      <Plus className="h-4 w-4 mr-2" />
                      添加连接
                    </Button>
                  }
                />
              ) : (
                <div className="divide-y">
                  {connections.map((conn) => (
                    <div key={conn.id} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                      <div className="flex items-center gap-4">
                        <div className="p-2 rounded-lg bg-slate-500/10">
                          <Database className="h-5 w-5 text-slate-600 dark:text-slate-400" />
                        </div>
                        <div>
                          <p className="font-medium">{conn.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {conn.db_type?.toUpperCase()} · {conn.host}:{conn.port}/{conn.database}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={conn.is_active ? 'default' : 'secondary'}>
                          {conn.is_active ? t('dataSources.active') : t('dataSources.inactive')}
                        </Badge>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setDeleteTarget({ type: 'connection', id: conn.id, name: conn.name })}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t('common.delete')}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 已上传文件 Tab */}
        <TabsContent value="files">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <FileSpreadsheet className="h-5 w-5" />
                  已上传文件
                </CardTitle>
                <CardDescription>管理上传的数据文件，支持 CSV、Excel、JSON、Parquet 格式</CardDescription>
              </div>
              <Button onClick={() => setShowUploadDialog(true)}>
                <Upload className="h-4 w-4 mr-2" />
                上传文件
              </Button>
            </CardHeader>
            <CardContent>
              {filesLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : files.length === 0 ? (
                <EmptyState
                  icon={FileSpreadsheet}
                  title="暂无上传文件"
                  description="上传 CSV、Excel 等数据文件开始分析"
                  action={
                    <Button onClick={() => setShowUploadDialog(true)}>
                      <Upload className="h-4 w-4 mr-2" />
                      上传文件
                    </Button>
                  }
                />
              ) : (
                <div className="divide-y">
                  {files.map((file) => (
                    <div key={file.id} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                      <div className="flex items-center gap-4">
                        <div className="p-2 rounded-lg bg-emerald-500/10">
                          <FileSpreadsheet className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                          <p className="font-medium">{file.original_name}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatFileSize(file.file_size)} · {file.row_count?.toLocaleString() || '-'} 行 ·{' '}
                            {formatDate(file.create_time)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={file.status === 'ready' ? 'default' : 'secondary'}>
                          {file.status === 'ready' ? '就绪' : file.status === 'processing' ? '处理中' : '错误'}
                        </Badge>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              className="text-destructive"
                              onClick={() => setDeleteTarget({ type: 'file', id: file.id, name: file.original_name })}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t('common.delete')}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* 数据对象 Tab */}
        <TabsContent value="raw-data">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HardDrive className="h-5 w-5" />
                数据对象
              </CardTitle>
              <CardDescription>系统自动从数据库连接和上传文件创建的数据对象，可用于构建数据源</CardDescription>
            </CardHeader>
            <CardContent>
              {rawLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : rawDataList.length === 0 ? (
                <EmptyState
                  icon={HardDrive}
                  title="暂无数据对象"
                  description="添加数据库连接或上传文件后，系统会自动创建数据对象"
                />
              ) : (
                <div className="divide-y">
                  {rawDataList.map((raw) => (
                    <div key={raw.id} className="flex items-center justify-between py-4 first:pt-0 last:pb-0">
                      <div className="flex items-center gap-4">
                        <div className="p-2 rounded-lg bg-cyan-500/10">
                          <HardDrive className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
                        </div>
                        <div>
                          <p className="font-medium">{raw.name}</p>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Badge variant="outline" className="text-xs">
                              {raw.raw_type === 'database_table' ? '数据库表' : '文件'}
                            </Badge>
                            {raw.columns_schema && <span>{raw.columns_schema.length} 列</span>}
                            {raw.row_count_estimate && <span>约 {raw.row_count_estimate.toLocaleString()} 行</span>}
                          </div>
                        </div>
                      </div>
                      <Badge variant={raw.status === 'ready' ? 'default' : 'secondary'}>
                        {raw.status === 'ready' ? '就绪' : raw.status === 'syncing' ? '同步中' : raw.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 对话框 */}
      <CreateDataSourceDialog open={showCreateDataSourceDialog} onOpenChange={setShowCreateDataSourceDialog} />
      <AddDatabaseDialog open={showAddDbDialog} onOpenChange={setShowAddDbDialog} />
      <UploadFileDialog open={showUploadDialog} onOpenChange={setShowUploadDialog} />

      {previewDataSourceId && (
        <DataSourcePreviewDialog
          dataSourceId={previewDataSourceId}
          open={!!previewDataSourceId}
          onOpenChange={(open) => !open && setPreviewDataSourceId(null)}
        />
      )}

      {/* 删除确认对话框 */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('dataSources.confirmDeleteTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('dataSources.confirmDelete', { name: deleteTarget?.name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
