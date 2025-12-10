import { Database, Loader2, Plus, RefreshCw, Trash2, Upload } from 'lucide-react';
import { useState } from 'react';

import {
  type DatabaseConnectionResponse,
  type DataSourceResponse,
  type UploadedFileResponse,
  useDataSourcePreview,
  useDataSources,
  useDbConnections,
  useDeleteDataSource,
  useDeleteDbConnection,
  useDeleteFile,
  useFiles,
  useSyncDataSourceSchema,
} from '@/api';
import { EmptyState, LoadingState } from '@/components/common';
import { AddDatabaseDialog } from '@/components/data-source/AddDatabaseDialog';
import { DataSourceWizardDialog } from '@/components/data-source/DataSourceWizardDialog';
import { UploadFileDialog } from '@/components/data-source/UploadFileDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useConfirmDialog, useToast } from '@/hooks';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 10;

const formatDate = (value?: string | null) => {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const TargetFields = ({ data }: { data?: DataSourceResponse['target_fields'] }) => {
  if (!data || data.length === 0) {
    return <p className="text-sm text-muted-foreground">未定义目标字段</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {data.map((field) => (
        <Badge key={field.name} variant="outline" className="text-xs">
          {field.name} · {field.data_type}
        </Badge>
      ))}
    </div>
  );
};

const RawMappings = ({ data }: { data?: DataSourceResponse['raw_mappings'] }) => {
  if (!data || data.length === 0) {
    return <p className="text-sm text-muted-foreground">暂未关联原始数据</p>;
  }

  return (
    <div className="space-y-1">
      {data.map((mapping) => (
        <div key={mapping.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
          <div className="flex flex-col">
            <span className="font-medium">{mapping.raw_data_name ?? `Raw #${mapping.raw_data_id}`}</span>
            <span className="text-muted-foreground text-xs">
              字段映射 {Object.keys(mapping.field_mappings || {}).length} 个
            </span>
          </div>
          {mapping.is_enabled === false ? (
            <Badge variant="outline">已禁用</Badge>
          ) : (
            <Badge variant="secondary">已启用</Badge>
          )}
        </div>
      ))}
    </div>
  );
};

const DataSourcePreviewDialog = ({
  open,
  onOpenChange,
  dataSourceId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  dataSourceId: number | null;
}) => {
  const { data, isLoading } = useDataSourcePreview(dataSourceId ?? undefined, { limit: 30 });

  const columns = data?.data.data?.columns ?? [];
  const rows = data?.data.data?.rows ?? [];
  const sourceStats = data?.data.data?.source_stats ?? {};

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>数据源预览</DialogTitle>
        </DialogHeader>
        {isLoading ? (
          <div className="py-12">
            <LoadingState />
          </div>
        ) : rows.length === 0 ? (
          <EmptyState title="暂无数据" description="该数据源暂时没有可预览的数据" icon={Database} />
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              {Object.entries(sourceStats).map(([name, count]) => (
                <Badge key={name} variant="outline">
                  {name}: {count} 行
                </Badge>
              ))}
            </div>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    {columns.map((col) => (
                      <TableHead key={col.name}>{col.name}</TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row) => {
                    const compositeKey =
                      columns.map((col) => String(row?.[col.name] ?? '')).join('|') || JSON.stringify(row);
                    return (
                      <TableRow key={compositeKey}>
                        {columns.map((col) => (
                          <TableCell key={col.name} className="max-w-[220px] truncate">
                            {String(row[col.name] ?? '')}
                          </TableCell>
                        ))}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export const DataSources = () => {
  const { toast } = useToast();
  const { confirm, ConfirmDialog } = useConfirmDialog();

  const [keyword, setKeyword] = useState('');
  const [pageNum, setPageNum] = useState(1);
  const [previewId, setPreviewId] = useState<number | null>(null);
  const [showAddDatabase, setShowAddDatabase] = useState(false);
  const [showUploadFile, setShowUploadFile] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<number | null>(null);
  const [deletingConnId, setDeletingConnId] = useState<number | null>(null);

  const { data, isLoading, isFetching, refetch } = useDataSources({
    page_num: pageNum,
    page_size: PAGE_SIZE,
    keyword: keyword.trim() || undefined,
  });
  const { data: filesResp, isLoading: loadingFiles } = useFiles();
  const { data: connsResp, isLoading: loadingConns } = useDbConnections();

  const total = data?.data.data?.total ?? 0;
  const items = (data?.data.data?.items ?? []) as DataSourceResponse[];
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const files = (filesResp?.data.data?.items ?? []) as UploadedFileResponse[];
  const connections = (connsResp?.data.data?.items ?? []) as DatabaseConnectionResponse[];

  const deleteMutation = useDeleteDataSource();
  const deleteFileMutation = useDeleteFile();
  const deleteConnMutation = useDeleteDbConnection();
  const syncMutation = useSyncDataSourceSchema();

  const handleDelete = async (id: number, name: string) => {
    const ok = await confirm({
      title: '确认删除数据源',
      description: `删除后将无法恢复：${name}`,
      confirmText: '删除',
      cancelText: '取消',
      variant: 'destructive',
    });

    if (!ok) return;

    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast({ title: '删除成功', description: '数据源已删除' });
      },
    });
  };

  const handleSync = (id: number) => {
    syncMutation.mutate(id, {
      onSuccess: () => {
        toast({ title: '刷新成功', description: 'Schema 已刷新' });
      },
      onError: (error) => {
        toast({ title: '刷新失败', description: error.message, variant: 'destructive' });
      },
      onSettled: () => {
        refetch();
      },
    });
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return '--';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const renderFileItem = (file: UploadedFileResponse) => (
    <div
      key={file.id}
      className="flex items-center justify-between gap-3 rounded-lg border p-3 hover:bg-muted/60 transition-colors"
    >
      <div className="flex items-center gap-3 min-w-0">
        <Upload className="h-4 w-4 text-teal-600 dark:text-teal-300 shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{file.original_name}</p>
          <p className="text-xs text-muted-foreground truncate">
            {file.file_type?.toUpperCase?.() || file.mime_type || '文件'} · {formatBytes(file.file_size)}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge variant="outline" className="shrink-0">
          {file.row_count ?? '--'} 行 / {file.column_count ?? '--'} 列
        </Badge>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          disabled={deletingFileId === file.id || deleteFileMutation.isPending}
          onClick={async () => {
            const ok = await confirm({
              title: '删除文件',
              description: `确认删除文件：${file.original_name}？`,
              confirmText: '删除',
              cancelText: '取消',
              variant: 'destructive',
            });
            if (!ok) return;
            setDeletingFileId(file.id);
            deleteFileMutation.mutate(file.id, {
              onSuccess: () => toast({ title: '删除成功', description: '文件已删除' }),
              onError: (error) => toast({ title: '删除失败', description: error.message, variant: 'destructive' }),
              onSettled: () => setDeletingFileId(null),
            });
          }}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );

  const renderConnectionItem = (conn: DatabaseConnectionResponse) => (
    <div
      key={conn.id}
      className="flex items-center justify-between gap-3 rounded-lg border p-3 hover:bg-muted/60 transition-colors"
    >
      <div className="flex items-center gap-3 min-w-0">
        <Database className="h-4 w-4 text-slate-600 dark:text-slate-300 shrink-0" />
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{conn.name}</p>
          <p className="text-xs text-muted-foreground truncate">
            {conn.db_type?.toUpperCase?.()} · {conn.host}:{conn.port}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge variant={conn.is_active ? 'secondary' : 'outline'} className="shrink-0">
          {conn.is_active ? '可用' : '不可用'}
        </Badge>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          disabled={deletingConnId === conn.id || deleteConnMutation.isPending}
          onClick={async () => {
            const ok = await confirm({
              title: '删除数据库连接',
              description: `确认删除连接：${conn.name}？`,
              confirmText: '删除',
              cancelText: '取消',
              variant: 'destructive',
            });
            if (!ok) return;
            setDeletingConnId(conn.id);
            deleteConnMutation.mutate(conn.id, {
              onSuccess: () => toast({ title: '删除成功', description: '连接已删除' }),
              onError: (error) => toast({ title: '删除失败', description: error.message, variant: 'destructive' }),
              onSettled: () => setDeletingConnId(null),
            });
          }}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );

  return (
    <div className="container py-8 max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">数据源</h1>
          <p className="text-muted-foreground mt-1">
            显示后端已存在的数据源，可查看字段、原始数据映射，并刷新 Schema。
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => setShowWizard(true)}>
            <Plus className="h-4 w-4 mr-2" />
            创建数据源
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className={cn('h-4 w-4 mr-2', isFetching && 'animate-spin')} />
            刷新列表
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3 w-full md:w-auto">
            <Input
              placeholder="按名称、描述搜索"
              value={keyword}
              onChange={(e) => {
                setPageNum(1);
                setKeyword(e.target.value);
              }}
              className="w-full md:w-72"
            />
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            共 {total} 个数据源 · 第 {pageNum}/{totalPages} 页
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingState />
      ) : items.length === 0 ? (
        <EmptyState title="暂无数据源" description="创建数据源后即可在此查看。" icon={Database} />
      ) : (
        <div className="space-y-4">
          {items.map((ds) => {
            const targetFields = ds.target_fields ?? [];
            const rawMappings = ds.raw_mappings ?? [];
            return (
              <Card key={ds.id} className="border-muted">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-xl">{ds.name}</CardTitle>
                      </div>
                      <p className="text-muted-foreground text-sm">{ds.description || '暂无描述'}</p>
                      <p className="text-xs text-muted-foreground">创建时间：{formatDate(ds.create_time)}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => setPreviewId(ds.id)}>
                        预览
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSync(ds.id)}
                        disabled={syncMutation.isPending}
                      >
                        {syncMutation.isPending ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4 mr-2" />
                        )}
                        刷新 Schema
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(ds.id, ds.name)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        删除
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex flex-wrap gap-3 text-sm">
                    <Badge variant="outline">目标字段 {targetFields.length}</Badge>
                    <Badge variant="outline">原始数据映射 {rawMappings.length}</Badge>
                    <Badge variant="outline">Schema 缓存 {ds.schema_cache ? '可用' : '暂无'}</Badge>
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold">目标字段</h3>
                    <TargetFields data={targetFields} />
                  </div>

                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold">原始数据映射</h3>
                    <RawMappings data={rawMappings} />
                  </div>
                </CardContent>
              </Card>
            );
          })}

          <div className="flex items-center justify-between rounded-md border bg-muted/50 px-4 py-3">
            <div className="text-sm text-muted-foreground">
              共 {total} 条 · 当前第 {pageNum} / {totalPages} 页
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={pageNum <= 1}
                onClick={() => setPageNum((p) => Math.max(1, p - 1))}
              >
                上一页
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={pageNum >= totalPages}
                onClick={() => setPageNum((p) => Math.min(totalPages, p + 1))}
              >
                下一页
              </Button>
            </div>
          </div>
        </div>
      )}

      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base">快速创建数据对象</CardTitle>
        </CardHeader>
        <CardContent className="p-4 grid gap-2 sm:grid-cols-2">
          <div className="flex items-start gap-3 rounded-lg border p-3">
            <div className="mt-0.5 rounded-md bg-muted/70 p-2">
              <Upload className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="space-y-1 flex-1">
              <p className="font-medium text-sm">上传文件</p>
              <p className="text-xs text-muted-foreground">CSV / Excel / Parquet / JSON</p>
              <Button size="sm" variant="outline" onClick={() => setShowUploadFile(true)}>
                <Upload className="h-4 w-4 mr-2" />
                上传文件
              </Button>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-lg border p-3">
            <div className="mt-0.5 rounded-md bg-muted/70 p-2">
              <Database className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="space-y-1 flex-1">
              <p className="font-medium text-sm">配置数据库</p>
              <p className="text-xs text-muted-foreground">接入 MySQL / PostgreSQL / SQLite</p>
              <Button size="sm" variant="outline" onClick={() => setShowAddDatabase(true)}>
                <Database className="h-4 w-4 mr-2" />
                新建连接
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">已上传文件</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {loadingFiles ? (
              <LoadingState />
            ) : files.length === 0 ? (
              <EmptyState icon={Upload} title="暂无文件" description="上传文件后即可在此查看并用于构建数据源。" />
            ) : (
              <ScrollArea className="h-[220px] pr-2">
                <div className="space-y-2">{files.map(renderFileItem)}</div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">数据库连接</CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            {loadingConns ? (
              <LoadingState />
            ) : connections.length === 0 ? (
              <EmptyState
                icon={Database}
                title="暂无数据库连接"
                description="配置数据库连接后，可在此选择表构建数据源。"
              />
            ) : (
              <ScrollArea className="h-[220px] pr-2">
                <div className="space-y-2">{connections.map(renderConnectionItem)}</div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>

      <DataSourcePreviewDialog
        open={previewId !== null}
        onOpenChange={(open) => {
          if (!open) setPreviewId(null);
        }}
        dataSourceId={previewId}
      />
      <AddDatabaseDialog open={showAddDatabase} onOpenChange={setShowAddDatabase} />
      <UploadFileDialog open={showUploadFile} onOpenChange={setShowUploadFile} />
      <DataSourceWizardDialog open={showWizard} onOpenChange={setShowWizard} />
      <ConfirmDialog />
    </div>
  );
};
