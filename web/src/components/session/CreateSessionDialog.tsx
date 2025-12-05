import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { CheckCircle2, Database, Loader2, MessageSquare } from 'lucide-react';
import { useDataSources, useCreateSession, type DataSourceResponse } from '@/api';
import { Button } from '@/components/ui/button';
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
export const CreateSessionDialog = ({ open, onOpenChange }: CreateSessionDialogProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [selectedIds, setSelectedIds] = useState<number[]>([]);

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

  const toggleDataSource = (id: number) => {
    const newIds = selectedIds.includes(id) ? selectedIds.filter((i) => i !== id) : [...selectedIds, id];
    setSelectedIds(newIds);
    setValue('data_source_ids', newIds);
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
    onOpenChange(false);
  };

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
            <ScrollArea className="h-[200px] border rounded-lg">
              {isLoadingDataSources ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
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
                <div className="p-2 space-y-1">
                  {dataSources.map((ds) => (
                    <button
                      key={ds.id}
                      type="button"
                      className={cn(
                        'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors',
                        selectedIds.includes(ds.id)
                          ? 'bg-primary/10 border border-primary'
                          : 'hover:bg-muted border border-transparent'
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
                  ))}
                </div>
              )}
            </ScrollArea>
            <p className="text-xs text-muted-foreground">{t('sessions.selectedCount', { count: selectedIds.length })}</p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={isSubmitting || selectedIds.length === 0 || createSessionMutation.isPending}>
              {(isSubmitting || createSessionMutation.isPending) && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {t('sessions.create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
