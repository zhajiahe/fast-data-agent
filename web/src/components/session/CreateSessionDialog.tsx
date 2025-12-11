import { Check, Database, Layers, MessageSquare } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useCreateSession, useDataSources } from '@/api';
import { LoadingSpinner } from '@/components/common';
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

/**
 * 创建分析会话对话框
 */
export const CreateSessionDialog = ({ open, onOpenChange }: CreateSessionDialogProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const navigate = useNavigate();

  // 获取数据源列表
  const { data: dataSourcesRes, isLoading: dsLoading } = useDataSources({ page_size: 100 });
  const dataSources = dataSourcesRes?.data.data?.items || [];

  const createSessionMutation = useCreateSession();

  // 表单状态
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedDataSourceId, setSelectedDataSourceId] = useState<string | null>(null);
  const [nameError, setNameError] = useState('');

  const validateForm = (): boolean => {
    if (!name.trim()) {
      setNameError('请输入会话名称');
      return false;
    }
    if (name.length > 50) {
      setNameError('名称最多 50 个字符');
      return false;
    }
    setNameError('');
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      const result = await createSessionMutation.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        data_source_id: selectedDataSourceId ?? undefined,
      });

      toast({
        title: t('common.success'),
        description: t('sessions.createSuccess'),
      });

      handleClose();

      // 导航到新创建的会话
      const sessionId = result.data.data?.id;
      if (sessionId) {
        navigate(`/chat/${sessionId}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '创建失败';
      toast({
        title: t('common.error'),
        description: msg,
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setSelectedDataSourceId(null);
    setNameError('');
    onOpenChange(false);
  };

  const toggleDataSource = (id: string) => {
    if (selectedDataSourceId === id) {
      setSelectedDataSourceId(null);
    } else {
      setSelectedDataSourceId(id);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            {t('sessions.create')}
          </DialogTitle>
          <DialogDescription>{t('sessions.createDesc')}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 会话名称 */}
          <div className="space-y-2">
            <Label htmlFor="name">{t('sessions.name')}</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：销售数据分析" />
            {nameError && <p className="text-sm text-destructive">{nameError}</p>}
          </div>

          {/* 描述 */}
          <div className="space-y-2">
            <Label htmlFor="description">{t('sessions.description')}</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="可选的描述信息"
              rows={2}
            />
          </div>

          {/* 选择数据源 */}
          <div className="space-y-2">
            <Label>{t('sessions.selectDataSources')}</Label>
            {dsLoading ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : dataSources.length === 0 ? (
              <div className="text-center py-6 border rounded-lg bg-muted/30">
                <Layers className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                <p className="text-sm text-muted-foreground mb-2">{t('sessions.noDataSources')}</p>
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
              <ScrollArea className="h-[200px] border rounded-lg">
                <div className="p-2 space-y-1">
                  {dataSources.map((ds) => (
                    <button
                      type="button"
                      key={ds.id}
                      onClick={() => toggleDataSource(ds.id)}
                      className={cn(
                        'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors',
                        selectedDataSourceId === ds.id
                          ? 'bg-primary/10 border border-primary'
                          : 'hover:bg-muted border border-transparent'
                      )}
                    >
                      <div
                        className={cn(
                          'p-2 rounded-lg',
                          selectedDataSourceId === ds.id ? 'bg-primary text-primary-foreground' : 'bg-muted'
                        )}
                      >
                        <Database className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{ds.name}</p>
                        {ds.description && <p className="text-xs text-muted-foreground truncate">{ds.description}</p>}
                      </div>
                      {selectedDataSourceId === ds.id && <Check className="h-4 w-4 text-primary shrink-0" />}
                    </button>
                  ))}
                </div>
              </ScrollArea>
            )}
            {selectedDataSourceId && (
              <p className="text-xs text-muted-foreground">{t('sessions.selectedCount', { count: 1 })}</p>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={handleClose}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={createSessionMutation.isPending}>
              {createSessionMutation.isPending && <LoadingSpinner size="sm" className="mr-2 text-current" />}
              {t('sessions.create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
