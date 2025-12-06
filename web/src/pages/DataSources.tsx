import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  Eye,
  FileSpreadsheet,
  FolderOpen,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { type DataSourceResponse, useDataSources, useDeleteDataSource, useSyncDataSourceSchema } from '@/api';
import { EmptyState, LoadingState } from '@/components/common';
import { AddDatabaseDialog } from '@/components/data-source/AddDatabaseDialog';
import { DataPreviewDialog } from '@/components/data-source/DataPreviewDialog';
import { UploadFileDialog } from '@/components/data-source/UploadFileDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useConfirmDialog, useToast } from '@/hooks';
import { cn } from '@/lib/utils';

interface GroupedDataSources {
  groupName: string | null;
  dataSources: DataSourceResponse[];
}

/**
 * 数据源管理页面
 */
export const DataSources = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [showAddDatabase, setShowAddDatabase] = useState(false);
  const [showUploadFile, setShowUploadFile] = useState(false);
  const [previewDataSource, setPreviewDataSource] = useState<DataSourceResponse | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['__ungrouped__']));
  const { confirm, ConfirmDialog } = useConfirmDialog();

  const { data: response, isLoading } = useDataSources();
  const deleteDataSourceMutation = useDeleteDataSource();
  const syncSchemaMutation = useSyncDataSourceSchema();

  const dataSources = response?.data.data?.items || [];

  // 按 group_name 分组
  const groupedDataSources = useMemo(() => {
    const groups: Map<string, DataSourceResponse[]> = new Map();
    const ungrouped: DataSourceResponse[] = [];

    for (const ds of dataSources) {
      if (ds.group_name) {
        const existing = groups.get(ds.group_name) || [];
        groups.set(ds.group_name, [...existing, ds]);
      } else {
        ungrouped.push(ds);
      }
    }

    const result: GroupedDataSources[] = [];

    // 先添加分组的数据源
    for (const [groupName, items] of groups) {
      result.push({ groupName, dataSources: items });
    }

    // 最后添加未分组的数据源
    if (ungrouped.length > 0) {
      result.push({ groupName: null, dataSources: ungrouped });
    }

    return result;
  }, [dataSources]);

  const toggleGroup = (groupKey: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) {
        next.delete(groupKey);
      } else {
        next.add(groupKey);
      }
      return next;
    });
  };

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
      return <Database className="h-5 w-5 text-slate-600 dark:text-slate-400" />;
    }
    return <FileSpreadsheet className="h-5 w-5 text-teal-600 dark:text-teal-400" />;
  };

  const getStatusBadge = (_ds: DataSourceResponse) => {
    const isActive = true;
    if (isActive) {
      return (
        <Badge
          variant="outline"
          className="text-teal-600 border-teal-300 bg-teal-50 dark:bg-teal-950 dark:border-teal-800"
        >
          <CheckCircle2 className="h-3 w-3 mr-1" />
          {t('dataSources.active')}
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="text-red-600 border-red-300 bg-red-50 dark:bg-red-950 dark:border-red-800">
        <AlertCircle className="h-3 w-3 mr-1" />
        {t('dataSources.inactive')}
      </Badge>
    );
  };

  const renderDataSourceCard = (ds: DataSourceResponse) => (
    <Card key={ds.id} className="group hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          {/* 可点击区域：图标和标题 */}
          <div
            className={cn(
              'flex items-center gap-3 flex-1 min-w-0',
              ds.source_type === 'file' && ds.file_id && 'cursor-pointer hover:opacity-80 transition-opacity'
            )}
            onClick={() => ds.source_type === 'file' && ds.file_id && setPreviewDataSource(ds)}
            onKeyDown={(e) => {
              if ((e.key === 'Enter' || e.key === ' ') && ds.source_type === 'file' && ds.file_id) {
                setPreviewDataSource(ds);
              }
            }}
            tabIndex={ds.source_type === 'file' && ds.file_id ? 0 : undefined}
            role={ds.source_type === 'file' && ds.file_id ? 'button' : undefined}
          >
            {getTypeIcon(ds)}
            <div className="min-w-0">
              <CardTitle className="text-base truncate">{ds.name}</CardTitle>
              <CardDescription className="text-xs">
                {ds.source_type === 'database' ? ds.db_type?.toUpperCase() : t('dataSources.file')}
              </CardDescription>
            </div>
          </div>
          {/* 菜单按钮 - 独立于可点击区域 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {ds.source_type === 'file' && ds.file_id && (
                <DropdownMenuItem onClick={() => setPreviewDataSource(ds)}>
                  <Eye className="h-4 w-4 mr-2" />
                  {t('dataSources.previewData')}
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={() => handleSyncSchema(ds.id)}>
                <RefreshCw className="h-4 w-4 mr-2" />
                {t('dataSources.refreshSchema')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => handleDelete(ds.id, ds.name)}>
                <Trash2 className="h-4 w-4 mr-2 text-destructive" />
                <span className="text-destructive">{t('common.delete')}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          {getStatusBadge(ds)}
          {ds.create_time && (
            <span className="text-xs text-muted-foreground">{new Date(ds.create_time).toLocaleDateString()}</span>
          )}
        </div>
        {ds.description && <p className="text-sm text-muted-foreground mt-3 line-clamp-2">{ds.description}</p>}
      </CardContent>
    </Card>
  );

  return (
    <div className="container py-8 max-w-6xl">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('dataSources.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('dataSources.subtitle')}</p>
        </div>
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

      {/* 数据源列表 */}
      {isLoading ? (
        <LoadingState />
      ) : dataSources.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-0">
            <EmptyState
              icon={Database}
              title={t('dataSources.empty')}
              description={t('dataSources.emptyHint')}
              action={
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
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {groupedDataSources.map((group) => {
            const groupKey = group.groupName || '__ungrouped__';
            const isExpanded = expandedGroups.has(groupKey);

            // 如果是分组
            if (group.groupName) {
              return (
                <Collapsible key={groupKey} open={isExpanded} onOpenChange={() => toggleGroup(groupKey)}>
                  <CollapsibleTrigger asChild>
                    <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50 hover:bg-muted cursor-pointer transition-colors">
                      {isExpanded ? (
                        <ChevronDown className="h-5 w-5 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-5 w-5 text-muted-foreground" />
                      )}
                      <FolderOpen className="h-5 w-5 text-amber-500" />
                      <span className="font-medium">{group.groupName}</span>
                      <Badge variant="secondary" className="ml-auto">
                        {t('dataSources.filesCount', { count: group.dataSources.length })}
                      </Badge>
                    </div>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mt-4 pl-8">
                      {group.dataSources.map(renderDataSourceCard)}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              );
            }

            // 未分组的数据源直接显示
            return (
              <div key={groupKey}>
                {groupedDataSources.length > 1 && (
                  <div className="flex items-center gap-2 mb-4 text-muted-foreground">
                    <Database className="h-4 w-4" />
                    <span className="text-sm font-medium">{t('dataSources.ungrouped')}</span>
                  </div>
                )}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {group.dataSources.map(renderDataSourceCard)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <AddDatabaseDialog open={showAddDatabase} onOpenChange={setShowAddDatabase} />
      <UploadFileDialog open={showUploadFile} onOpenChange={setShowUploadFile} />
      <DataPreviewDialog
        open={!!previewDataSource}
        onOpenChange={(open) => !open && setPreviewDataSource(null)}
        fileId={previewDataSource?.file_id || null}
        dataSourceName={previewDataSource?.name || ''}
      />
      <ConfirmDialog />
    </div>
  );
};
