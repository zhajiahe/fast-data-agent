// @ts-nocheck
import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle2, ChevronDown, ChevronRight, Database, FolderOpen, MessageSquare } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { type DataSourceResponse, useCreateSession, useDataSources } from '@/api';
import { LoadingSpinner } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface CreateSessionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialSelectedIds?: number[];
}

interface GroupedDataSources {
  groupName: string | null;
  dataSources: DataSourceResponse[];
}

const formSchema = z.object({
  name: z.string().min(1, '请输入会话名称').max(100, '名称最多 100 个字符'),
  description: z.string().max(500, '描述最多 500 个字符').optional(),
  data_source_ids: z.array(z.number()).min(1, '请至少选择一个数据源'),
});

type FormData = z.infer<typeof formSchema>;

/**
 * 创建会话对话框
 */
export const CreateSessionDialog = ({ open, onOpenChange, initialSelectedIds = [] }: CreateSessionDialogProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['__ungrouped__']));

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      data_source_ids: [],
    },
  });

  // 使用生成的 API hooks
  const { data: dataSourcesResponse, isLoading: isLoadingDataSources } = useDataSources();
  const createSessionMutation = useCreateSession();

  const dataSources: DataSourceResponse[] = dataSourcesResponse?.data.data?.items || [];

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

  // 打开时应用初始选中项
  useEffect(() => {
    if (open) {
      const initial = initialSelectedIds || [];
      setSelectedIds(initial);
      setValue('data_source_ids', initial);
    }
  }, [open, initialSelectedIds, setValue]);

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

  const toggleDataSource = (id: number) => {
    const newIds = selectedIds.includes(id) ? selectedIds.filter((i) => i !== id) : [...selectedIds, id];
    setSelectedIds(newIds);
    setValue('data_source_ids', newIds);
  };

  const toggleGroupSelection = (group: GroupedDataSources) => {
    const groupIds = group.dataSources.map((ds) => ds.id);
    const allSelected = groupIds.every((id) => selectedIds.includes(id));

    let newIds: number[];
    if (allSelected) {
      // 取消选择组内所有
      newIds = selectedIds.filter((id) => !groupIds.includes(id));
    } else {
      // 选择组内所有
      newIds = [...new Set([...selectedIds, ...groupIds])];
    }
    setSelectedIds(newIds);
    setValue('data_source_ids', newIds);
  };

  const isGroupFullySelected = (group: GroupedDataSources) => {
    return group.dataSources.every((ds) => selectedIds.includes(ds.id));
  };

  const isGroupPartiallySelected = (group: GroupedDataSources) => {
    const selected = group.dataSources.filter((ds) => selectedIds.includes(ds.id));
    return selected.length > 0 && selected.length < group.dataSources.length;
  };

  const onSubmit = async (data: FormData) => {
    createSessionMutation.mutate(
      {
        name: data.name,
        description: data.description,
        data_source_ids: data.data_source_ids,
      },
      {
        onSuccess: (response) => {
          toast({
            title: t('common.success'),
            description: t('sessions.createSuccess'),
          });
          handleClose();
          // 跳转到新创建的会话
          const sessionId = response.data.data?.id;
          if (sessionId) {
            navigate(`/chat/${sessionId}`);
          }
        },
        onError: (err) => {
          toast({
            title: t('common.error'),
            description: err.message,
            variant: 'destructive',
          });
        },
      }
    );
  };

  const handleClose = () => {
    reset();
    setSelectedIds([]);
    setExpandedGroups(new Set(['__ungrouped__']));
    setValue('data_source_ids', []);
    onOpenChange(false);
  };

  const renderDataSourceItem = (ds: DataSourceResponse) => (
    <button
      key={ds.id}
      type="button"
      className={cn(
        'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors',
        selectedIds.includes(ds.id) ? 'bg-primary/10 border border-primary' : 'hover:bg-muted border border-transparent'
      )}
      onClick={() => toggleDataSource(ds.id)}
    >
      <div
        className={cn(
          'w-5 h-5 rounded border flex items-center justify-center shrink-0',
          selectedIds.includes(ds.id) ? 'bg-primary border-primary' : 'border-muted-foreground/30'
        )}
      >
        {selectedIds.includes(ds.id) && <CheckCircle2 className="h-3 w-3 text-primary-foreground" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">{ds.name}</p>
        <p className="text-xs text-muted-foreground">
          {ds.source_type === 'database' ? ds.db_type?.toUpperCase() : t('dataSources.file')}
        </p>
      </div>
    </button>
  );

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            {t('sessions.create')}
          </DialogTitle>
          <DialogDescription>{t('sessions.createDesc')}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* 名称 */}
          <div className="space-y-2">
            <Label htmlFor="name">{t('sessions.name')}</Label>
            <Input id="name" {...register('name')} placeholder="例如：Q4 销售数据分析" />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>

          {/* 描述 */}
          <div className="space-y-2">
            <Label htmlFor="description">{t('sessions.description')}</Label>
            <Textarea id="description" {...register('description')} placeholder="可选的描述信息" rows={2} />
          </div>

          {/* 选择数据源 */}
          <div className="space-y-2">
            <Label>{t('sessions.selectDataSources')}</Label>
            {errors.data_source_ids && <p className="text-sm text-destructive">{errors.data_source_ids.message}</p>}
            <ScrollArea className="h-[240px] border rounded-lg">
              {isLoadingDataSources ? (
                <div className="flex items-center justify-center h-full">
                  <LoadingSpinner size="md" />
                </div>
              ) : dataSources.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center p-4">
                  <Database className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">{t('sessions.noDataSources')}</p>
                  <Button
                    type="button"
                    variant="link"
                    size="sm"
                    onClick={() => {
                      handleClose();
                      navigate('/data-sources');
                    }}
                  >
                    {t('sessions.goToDataSources')}
                  </Button>
                </div>
              ) : (
                <div className="p-2 space-y-2">
                  {groupedDataSources.map((group) => {
                    const groupKey = group.groupName || '__ungrouped__';
                    const isExpanded = expandedGroups.has(groupKey);

                    // 如果是分组
                    if (group.groupName) {
                      const fullySelected = isGroupFullySelected(group);
                      const partiallySelected = isGroupPartiallySelected(group);

                      return (
                        <Collapsible key={groupKey} open={isExpanded} onOpenChange={() => toggleGroup(groupKey)}>
                          <div className="flex items-center gap-2">
                            {/* 组选择框 */}
                            <button
                              type="button"
                              className={cn(
                                'w-5 h-5 rounded border flex items-center justify-center shrink-0',
                                fullySelected
                                  ? 'bg-primary border-primary'
                                  : partiallySelected
                                    ? 'bg-primary/50 border-primary'
                                    : 'border-muted-foreground/30'
                              )}
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleGroupSelection(group);
                              }}
                            >
                              {(fullySelected || partiallySelected) && (
                                <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                              )}
                            </button>

                            <CollapsibleTrigger asChild>
                              <div className="flex-1 flex items-center gap-2 p-2 rounded-lg hover:bg-muted cursor-pointer transition-colors">
                                {isExpanded ? (
                                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                ) : (
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                )}
                                <FolderOpen className="h-4 w-4 text-amber-500" />
                                <span className="font-medium text-sm">{group.groupName}</span>
                                <span className="text-xs text-muted-foreground ml-auto">
                                  {t('dataSources.filesCount', { count: group.dataSources.length })}
                                </span>
                              </div>
                            </CollapsibleTrigger>
                          </div>
                          <CollapsibleContent>
                            <div className="pl-7 space-y-1 mt-1">{group.dataSources.map(renderDataSourceItem)}</div>
                          </CollapsibleContent>
                        </Collapsible>
                      );
                    }

                    // 未分组的数据源直接显示
                    return (
                      <div key={groupKey} className="space-y-1">
                        {groupedDataSources.length > 1 && (
                          <div className="flex items-center gap-2 px-2 py-1 text-muted-foreground">
                            <Database className="h-3 w-3" />
                            <span className="text-xs font-medium">{t('dataSources.ungrouped')}</span>
                          </div>
                        )}
                        {group.dataSources.map(renderDataSourceItem)}
                      </div>
                    );
                  })}
                </div>
              )}
            </ScrollArea>
            <p className="text-xs text-muted-foreground">
              {t('sessions.selectedCount', { count: selectedIds.length })}
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              {t('common.cancel')}
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || selectedIds.length === 0 || createSessionMutation.isPending}
            >
              {(isSubmitting || createSessionMutation.isPending) && (
                <LoadingSpinner size="sm" className="mr-2 text-current" />
              )}
              {t('sessions.create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
