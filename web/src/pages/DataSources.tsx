import {
  Database,
  Eye,
  FileSpreadsheet,
  HardDrive,
  HelpCircle,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  useDbConnections,
  useDeleteDbConnection,
  useDeleteFile,
  useDeleteRawData,
  useFiles,
  useRawDataList,
} from '@/api';
import { EmptyState } from '@/components/common';
import { AddDatabaseDialog } from '@/components/data-source/AddDatabaseDialog';
import { RawDataPreviewDialog } from '@/components/data-source/RawDataPreviewDialog';
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
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
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
 * 数据管理页面
 *
 * 整合数据库连接、文件上传、数据对象管理
 */
export const DataSources = () => {
  const { t } = useTranslation();
  const { toast } = useToast();

  // 对话框状态
  const [showAddDbDialog, setShowAddDbDialog] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);

  // 数据对象预览状态
  const [previewTarget, setPreviewTarget] = useState<{
    id: string;
    name: string;
  } | null>(null);

  // 删除确认状态
  const [deleteTarget, setDeleteTarget] = useState<{
    type: 'connection' | 'file' | 'rawData';
    id: string;
    name: string;
  } | null>(null);

  // API Hooks
  const { data: connectionsRes, isLoading: connLoading, refetch: refetchConn } = useDbConnections({ page_size: 100 });
  const { data: filesRes, isLoading: filesLoading, refetch: refetchFiles } = useFiles();
  const { data: rawDataRes, isLoading: rawLoading, refetch: refetchRaw } = useRawDataList({ page_size: 100 });

  const deleteConnectionMutation = useDeleteDbConnection();
  const deleteFileMutation = useDeleteFile();
  const deleteRawDataMutation = useDeleteRawData();

  // 数据提取
  const connections = connectionsRes?.data.data?.items || [];
  const files = filesRes?.data.data?.items || [];
  const rawDataList = rawDataRes?.data.data?.items || [];

  // 统计数据
  const stats = [
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
    refetchConn();
    refetchFiles();
    refetchRaw();
    toast({ title: t('common.success'), description: '数据已刷新' });
  };

  // 处理删除
  const handleDelete = async () => {
    if (!deleteTarget) return;

    try {
      if (deleteTarget.type === 'connection') {
        await deleteConnectionMutation.mutateAsync(deleteTarget.id);
      } else if (deleteTarget.type === 'file') {
        await deleteFileMutation.mutateAsync(deleteTarget.id);
      } else if (deleteTarget.type === 'rawData') {
        await deleteRawDataMutation.mutateAsync(deleteTarget.id);
      }
      toast({ title: t('common.success'), description: `${deleteTarget.name} 已删除` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '删除失败';
      toast({ title: t('common.error'), description: msg, variant: 'destructive' });
    } finally {
      setDeleteTarget(null);
    }
  };

  // 处理预览
  const handlePreview = (id: string, name: string) => {
    setPreviewTarget({ id, name });
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
      <div className="grid grid-cols-3 gap-4 mb-6">
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
      <TooltipProvider delayDuration={300}>
        <Tabs defaultValue="raw-data" className="space-y-4">
          <div className="flex items-center gap-2">
            <TabsList>
              <TabsTrigger value="raw-data" className="gap-2">
                <HardDrive className="h-4 w-4" />
                数据对象
              </TabsTrigger>
              <TabsTrigger value="connections" className="gap-2">
                <Database className="h-4 w-4" />
                数据库连接
              </TabsTrigger>
              <TabsTrigger value="files" className="gap-2">
                <FileSpreadsheet className="h-4 w-4" />
                已上传文件
              </TabsTrigger>
            </TabsList>
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="p-1 text-muted-foreground hover:text-foreground transition-colors">
                  <HelpCircle className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-xs">
                <div className="space-y-2 text-xs">
                  <p><strong>数据对象</strong>：从连接或文件自动生成，是原始数据的映射，可在会话中直接选择使用</p>
                  <p><strong>数据库连接</strong>：配置外部数据库（MySQL/PostgreSQL）的连接信息</p>
                  <p><strong>已上传文件</strong>：上传的 CSV/Excel 等数据文件</p>
                </div>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* 数据对象 Tab */}
          <TabsContent value="raw-data">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <HardDrive className="h-5 w-5" />
                  数据对象
                </CardTitle>
                <CardDescription>系统自动从数据库连接和上传文件创建的数据对象，可在创建会话时选择</CardDescription>
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
                    action={
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
                    }
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
                        <div className="flex items-center gap-2">
                          <Badge variant={raw.status === 'ready' ? 'default' : 'secondary'}>
                            {raw.status === 'ready' ? '就绪' : raw.status === 'syncing' ? '同步中' : raw.status}
                          </Badge>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => handlePreview(raw.id, raw.name)}>
                                <Eye className="h-4 w-4 mr-2" />
                                预览数据
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={() => setDeleteTarget({ type: 'rawData', id: raw.id, name: raw.name })}
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
        </Tabs>
      </TooltipProvider>

      {/* 对话框 */}
      <AddDatabaseDialog open={showAddDbDialog} onOpenChange={setShowAddDbDialog} />
      <UploadFileDialog open={showUploadDialog} onOpenChange={setShowUploadDialog} />
      <RawDataPreviewDialog
        open={!!previewTarget}
        onOpenChange={(open) => !open && setPreviewTarget(null)}
        rawDataId={previewTarget?.id ?? null}
        rawDataName={previewTarget?.name}
      />

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
