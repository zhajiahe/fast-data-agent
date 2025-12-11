import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowRight, Check, ChevronDown, HardDrive, Layers } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import {
  type FieldMapping as ApiFieldMapping,
  type TargetField as ApiTargetField,
  type RawDataResponse,
  useCreateDataSource,
  useRawDataList,
} from '@/api';
import { LoadingSpinner } from '@/components/common';
import { Badge } from '@/components/ui/badge';
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
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface CreateDataSourceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// 字段映射项：原始字段 -> 目标字段名
interface FieldMappingItem {
  sourceField: string; // 原始字段名
  targetField: string; // 映射后的目标字段名（空字符串表示不映射）
  dataType: string; // 数据类型
}

// 每个 RawData 的映射配置
interface RawDataMappingConfig {
  rawDataId: number;
  rawDataName: string;
  fields: FieldMappingItem[];
}

const formSchema = z.object({
  name: z.string().min(1, '请输入数据源名称').max(100, '名称最多 100 个字符'),
  description: z.string().max(500, '描述最多 500 个字符').optional(),
});

type FormData = z.infer<typeof formSchema>;

// 获取 RawData 的列信息
const getColumnsFromRawData = (rd: RawDataResponse): Array<{ name: string; dataType: string }> => {
  return (rd.columns_schema || [])
    .filter((col) => col.name)
    .map((col) => ({
      name: col.name || '',
      dataType: col.data_type || 'string',
    }));
};

/**
 * 创建数据源对话框
 *
 * 左侧选择原始数据表，右侧显示选中表的字段并配置映射
 */
export const CreateDataSourceDialog = ({ open, onOpenChange }: CreateDataSourceDialogProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();

  // 获取 RawData 列表
  const { data: rawDataRes, isLoading: rawLoading } = useRawDataList({ page_size: 100 });
  const rawDataList = rawDataRes?.data.data?.items || [];

  // 本地状态
  const [selectedRawDataIds, setSelectedRawDataIds] = useState<number[]>([]);
  const [mappingConfigs, setMappingConfigs] = useState<Map<number, RawDataMappingConfig>>(new Map());
  const [expandedRawData, setExpandedRawData] = useState<Set<number>>(new Set());

  const createDataSourceMutation = useCreateDataSource();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      description: '',
    },
  });

  // 获取选中的 RawData 详情
  const selectedRawData = useMemo(
    () => rawDataList.filter((rd) => selectedRawDataIds.includes(rd.id)),
    [rawDataList, selectedRawDataIds]
  );

  // 当选择 RawData 变化时，初始化映射配置（默认不映射）
  useEffect(() => {
    const newConfigs = new Map<number, RawDataMappingConfig>();

    for (const rd of selectedRawData) {
      // 如果已有配置则保留，否则新建
      const existing = mappingConfigs.get(rd.id);
      if (existing) {
        newConfigs.set(rd.id, existing);
      } else {
        const columns = getColumnsFromRawData(rd);
        newConfigs.set(rd.id, {
          rawDataId: rd.id,
          rawDataName: rd.name,
          fields: columns.map((col) => ({
            sourceField: col.name,
            targetField: '', // 默认不映射
            dataType: col.dataType,
          })),
        });
      }
    }

    setMappingConfigs(newConfigs);
    // 自动展开选中的表
    setExpandedRawData(new Set(selectedRawDataIds));
  }, [selectedRawDataIds, selectedRawData]);

  // 切换选择 RawData
  const toggleRawData = (id: number) => {
    setSelectedRawDataIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((i) => i !== id);
      }
      return [...prev, id];
    });
  };

  // 切换 RawData 展开状态
  const toggleExpanded = (id: number) => {
    setExpandedRawData((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // 更新字段映射
  const updateFieldMapping = (rawDataId: number, sourceField: string, targetField: string) => {
    setMappingConfigs((prev) => {
      const next = new Map(prev);
      const config = next.get(rawDataId);
      if (config) {
        const updatedFields = config.fields.map((f) => (f.sourceField === sourceField ? { ...f, targetField } : f));
        next.set(rawDataId, { ...config, fields: updatedFields });
      }
      return next;
    });
  };

  // 快速映射：将原始字段名设为目标字段名
  const quickMapAll = (rawDataId: number) => {
    setMappingConfigs((prev) => {
      const next = new Map(prev);
      const config = next.get(rawDataId);
      if (config) {
        const updatedFields = config.fields.map((f) => ({
          ...f,
          targetField: f.sourceField, // 使用原始字段名
        }));
        next.set(rawDataId, { ...config, fields: updatedFields });
      }
      return next;
    });
  };

  // 排除所有字段
  const excludeAllFields = (rawDataId: number) => {
    setMappingConfigs((prev) => {
      const next = new Map(prev);
      const config = next.get(rawDataId);
      if (config) {
        const updatedFields = config.fields.map((f) => ({ ...f, targetField: '-' }));
        next.set(rawDataId, { ...config, fields: updatedFields });
      }
      return next;
    });
  };

  // 重置为默认（留空使用原名）
  const resetMappings = (rawDataId: number) => {
    setMappingConfigs((prev) => {
      const next = new Map(prev);
      const config = next.get(rawDataId);
      if (config) {
        const updatedFields = config.fields.map((f) => ({ ...f, targetField: '' }));
        next.set(rawDataId, { ...config, fields: updatedFields });
      }
      return next;
    });
  };

  // 计算已映射的字段数（排除 '-' 的字段）
  const getMappedCount = (rawDataId: number): number => {
    const config = mappingConfigs.get(rawDataId);
    if (!config) return 0;
    // 留空也算映射（使用原名），只有 '-' 才算排除
    return config.fields.filter((f) => f.targetField.trim() !== '-').length;
  };

  const onSubmit = async (data: FormData) => {
    if (selectedRawDataIds.length === 0) {
      toast({ title: t('common.error'), description: '请至少选择一个原始数据', variant: 'destructive' });
      return;
    }

    // 收集所有目标字段（留空则使用原始字段名）
    const targetFieldsMap = new Map<string, { dataType: string }>();
    const rawMappings: ApiFieldMapping[] = [];

    for (const [rawDataId, config] of mappingConfigs) {
      const mappings: Record<string, string | null> = {};

      for (const field of config.fields) {
        // 如果目标字段为 '-' 则表示排除该字段
        if (field.targetField.trim() === '-') {
          continue;
        }
        // 留空则使用原始字段名，否则使用自定义名称
        const target = field.targetField.trim() || field.sourceField;
        // 记录目标字段
        if (!targetFieldsMap.has(target)) {
          targetFieldsMap.set(target, { dataType: field.dataType });
        }
        // 记录映射: target -> source
        mappings[target] = field.sourceField;
      }

      if (Object.keys(mappings).length > 0) {
        rawMappings.push({ raw_data_id: rawDataId, mappings });
      }
    }

    if (targetFieldsMap.size === 0) {
      toast({ title: t('common.error'), description: '没有可映射的字段', variant: 'destructive' });
      return;
    }

    // 构建目标字段列表
    const targetFields: ApiTargetField[] = Array.from(targetFieldsMap.entries()).map(([name, info]) => ({
      name,
      data_type: info.dataType,
    }));

    try {
      await createDataSourceMutation.mutateAsync({
        name: data.name,
        description: data.description,
        target_fields: targetFields,
        raw_mappings: rawMappings,
      });

      toast({ title: t('common.success'), description: t('dataSources.createSuccess') });
      handleClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '创建失败';
      toast({ title: t('common.error'), description: msg, variant: 'destructive' });
    }
  };

  const handleClose = () => {
    reset();
    setSelectedRawDataIds([]);
    setMappingConfigs(new Map());
    setExpandedRawData(new Set());
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[900px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            创建数据源
          </DialogTitle>
          <DialogDescription>选择原始数据表，配置字段映射（留空使用原字段名，输入 - 排除字段）</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex-1 flex flex-col min-h-0 space-y-4 overflow-hidden">
          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-4 shrink-0">
            <div className="space-y-2">
              <Label htmlFor="name">{t('dataSources.name')}</Label>
              <Input id="name" {...register('name')} placeholder="例如：销售数据汇总" />
              {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">{t('dataSources.description')}</Label>
              <Input id="description" {...register('description')} placeholder="可选的描述信息" />
            </div>
          </div>

          {/* 主体区域：左右分栏 */}
          <div className="flex-1 grid grid-cols-5 gap-4 min-h-0 overflow-hidden">
            {/* 左侧：选择原始数据（占 2 列） */}
            <div className="col-span-2 flex flex-col min-h-0 border rounded-lg overflow-hidden">
              <div className="px-3 py-2 border-b bg-muted/30 shrink-0">
                <h4 className="font-medium text-sm flex items-center gap-2">
                  <HardDrive className="h-4 w-4" />
                  选择原始数据
                  {selectedRawDataIds.length > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      已选 {selectedRawDataIds.length}
                    </Badge>
                  )}
                </h4>
              </div>
              {rawLoading ? (
                <div className="flex items-center justify-center py-12">
                  <LoadingSpinner />
                </div>
              ) : rawDataList.length === 0 ? (
                <div className="text-center py-8 px-4">
                  <HardDrive className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">暂无原始数据</p>
                  <p className="text-xs text-muted-foreground mt-1">请先连接数据库或上传文件</p>
                </div>
              ) : (
                <ScrollArea className="flex-1">
                  <div className="p-2 space-y-1">
                    {rawDataList.map((rd) => {
                      const isSelected = selectedRawDataIds.includes(rd.id);
                      const columns = getColumnsFromRawData(rd);
                      const mappedCount = isSelected ? getMappedCount(rd.id) : 0;

                      return (
                        <button
                          type="button"
                          key={rd.id}
                          onClick={() => toggleRawData(rd.id)}
                          className={cn(
                            'w-full flex items-center gap-2 p-2.5 rounded-lg text-left transition-colors',
                            isSelected
                              ? 'bg-primary/10 border border-primary'
                              : 'hover:bg-muted border border-transparent'
                          )}
                        >
                          <div
                            className={cn(
                              'p-1.5 rounded transition-colors shrink-0',
                              isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted'
                            )}
                          >
                            {isSelected ? <Check className="h-3.5 w-3.5" /> : <HardDrive className="h-3.5 w-3.5" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm truncate">{rd.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {rd.raw_type === 'database_table' ? '数据库表' : '文件'} · {columns.length} 列
                              {isSelected && mappedCount > 0 && (
                                <span className="text-primary ml-1">· 已映射 {mappedCount}</span>
                              )}
                            </p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </ScrollArea>
              )}
            </div>

            {/* 右侧：字段映射配置（占 3 列） */}
            <div className="col-span-3 flex flex-col min-h-0 border rounded-lg overflow-hidden">
              <div className="px-3 py-2 border-b bg-muted/30 shrink-0">
                <h4 className="font-medium text-sm flex items-center gap-2">
                  <ArrowRight className="h-4 w-4" />
                  字段映射
                </h4>
              </div>
              <ScrollArea className="flex-1">
                <div className="p-2 space-y-3">
                  {selectedRawDataIds.length === 0 ? (
                    <div className="text-center py-12 px-4">
                      <Layers className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
                      <p className="text-sm text-muted-foreground">请先在左侧选择原始数据</p>
                      <p className="text-xs text-muted-foreground mt-1">选择后可配置字段映射</p>
                    </div>
                  ) : (
                    selectedRawData.map((rd) => {
                      const config = mappingConfigs.get(rd.id);
                      const isExpanded = expandedRawData.has(rd.id);
                      const mappedCount = getMappedCount(rd.id);

                      return (
                        <Collapsible key={rd.id} open={isExpanded}>
                          <div className="border rounded-lg overflow-hidden">
                            {/* 表头 */}
                            <div className="flex items-center gap-2 px-3 py-2 bg-muted/30">
                              <CollapsibleTrigger asChild>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6 shrink-0"
                                  onClick={() => toggleExpanded(rd.id)}
                                >
                                  <ChevronDown
                                    className={cn('h-4 w-4 transition-transform', isExpanded && 'rotate-180')}
                                  />
                                </Button>
                              </CollapsibleTrigger>
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm truncate">{rd.name}</p>
                                <p className="text-xs text-muted-foreground">
                                  {config?.fields.length || 0} 个字段
                                  {mappedCount > 0 && <span className="text-primary ml-1">· 已映射 {mappedCount}</span>}
                                </p>
                              </div>
                              <div className="flex gap-1">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className="h-6 text-xs px-2"
                                  onClick={() => quickMapAll(rd.id)}
                                  title="使用原始字段名作为目标字段名"
                                >
                                  同名映射
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 text-xs px-2"
                                  onClick={() => resetMappings(rd.id)}
                                  title="重置为默认（留空使用原名）"
                                >
                                  重置
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 text-xs px-2 text-destructive"
                                  onClick={() => excludeAllFields(rd.id)}
                                  title="排除所有字段"
                                >
                                  全排除
                                </Button>
                              </div>
                            </div>

                            {/* 字段列表 */}
                            <CollapsibleContent>
                              <div className="p-3 space-y-2 bg-card">
                                {/* 表头说明 */}
                                <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground pb-1 border-b">
                                  <span>原始字段</span>
                                  <span>目标字段名（留空使用原名，- 排除）</span>
                                </div>
                                {config?.fields.map((field) => (
                                  <div key={field.sourceField} className="grid grid-cols-2 gap-3 items-center">
                                    <div className="flex items-center gap-2 text-sm">
                                      <span
                                        className={cn(
                                          'w-2 h-2 rounded-full shrink-0',
                                          field.targetField.trim() === '-' ? 'bg-destructive/50' : 'bg-teal-500'
                                        )}
                                      />
                                      <span className="font-mono truncate" title={field.sourceField}>
                                        {field.sourceField}
                                      </span>
                                      <Badge variant="outline" className="text-[10px] shrink-0">
                                        {field.dataType}
                                      </Badge>
                                    </div>
                                    <Input
                                      value={field.targetField}
                                      onChange={(e) => updateFieldMapping(rd.id, field.sourceField, e.target.value)}
                                      placeholder={field.sourceField}
                                      className="h-7 text-sm font-mono"
                                    />
                                  </div>
                                ))}
                              </div>
                            </CollapsibleContent>
                          </div>
                        </Collapsible>
                      );
                    })
                  )}
                </div>
              </ScrollArea>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0 pt-2 shrink-0">
            <Button type="button" variant="outline" onClick={handleClose}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={isSubmitting || createDataSourceMutation.isPending}>
              {(isSubmitting || createDataSourceMutation.isPending) && (
                <LoadingSpinner size="sm" className="mr-2 text-current" />
              )}
              创建数据源
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
