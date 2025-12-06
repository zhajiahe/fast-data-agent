import { zodResolver } from '@hookform/resolvers/zod';
import { Database } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { DatabaseType, DataSourceType, useCreateDataSource } from '@/api';
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';

interface AddDatabaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const databaseTypes: { value: (typeof DatabaseType)[keyof typeof DatabaseType]; label: string; defaultPort: number }[] =
  [
    { value: DatabaseType.postgresql, label: 'PostgreSQL', defaultPort: 5432 },
    { value: DatabaseType.mysql, label: 'MySQL', defaultPort: 3306 },
  ];

const formSchema = z.object({
  name: z.string().min(1, '请输入名称').max(50, '名称最多 50 个字符'),
  description: z.string().max(200, '描述最多 200 个字符').optional(),
  db_type: z.enum(['postgresql', 'mysql']),
  host: z.string().min(1, '请输入主机地址'),
  port: z
    .string()
    .transform((val) => Number(val))
    .pipe(z.number().min(0).max(65535)),
  database: z.string().min(1, '请输入数据库名'),
  username: z.string().min(1, '请输入用户名'),
  password: z.string().min(1, '请输入密码'),
});

type FormData = z.infer<typeof formSchema>;

/**
 * 添加数据库连接对话框
 */
export const AddDatabaseDialog = ({ open, onOpenChange }: AddDatabaseDialogProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      db_type: 'postgresql' as const,
      port: '5432',
    },
  });

  const dbType = watch('db_type');

  // 使用生成的 API hooks
  const createDataSourceMutation = useCreateDataSource();

  const handleDatabaseTypeChange = (value: 'postgresql' | 'mysql') => {
    setValue('db_type', value);
    const dbTypeConfig = databaseTypes.find((t) => t.value === value);
    if (dbTypeConfig) {
      setValue('port', String(dbTypeConfig.defaultPort));
    }
  };

  const onSubmit = async (data: FormData) => {
    createDataSourceMutation.mutate(
      {
        name: data.name,
        description: data.description,
        source_type: DataSourceType.database,
        db_config: {
          db_type: data.db_type as (typeof DatabaseType)[keyof typeof DatabaseType],
          host: data.host,
          port: data.port,
          database: data.database,
          username: data.username,
          password: data.password,
        },
      },
      {
        onSuccess: () => {
          toast({
            title: t('common.success'),
            description: t('dataSources.createSuccess'),
          });
          reset();
          onOpenChange(false);
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

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      reset();
    }
    onOpenChange(isOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            {t('dataSources.addDatabase')}
          </DialogTitle>
          <DialogDescription>{t('dataSources.addDatabaseDesc')}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* 名称 */}
          <div className="space-y-2">
            <Label htmlFor="name">{t('dataSources.name')}</Label>
            <Input id="name" {...register('name')} placeholder="例如：生产数据库" />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>

          {/* 描述 */}
          <div className="space-y-2">
            <Label htmlFor="description">{t('dataSources.description')}</Label>
            <Textarea id="description" {...register('description')} placeholder="可选的描述信息" rows={2} />
          </div>

          {/* 数据库类型 */}
          <div className="space-y-2">
            <Label>{t('dataSources.databaseType')}</Label>
            <Select value={dbType} onValueChange={handleDatabaseTypeChange}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {databaseTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* 连接信息 */}
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2 space-y-2">
              <Label htmlFor="host">{t('dataSources.host')}</Label>
              <Input id="host" {...register('host')} placeholder="localhost" />
              {errors.host && <p className="text-sm text-destructive">{errors.host.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="port">{t('dataSources.port')}</Label>
              <Input id="port" type="number" {...register('port')} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="database">{t('dataSources.database')}</Label>
            <Input id="database" {...register('database')} placeholder="数据库名" />
            {errors.database && <p className="text-sm text-destructive">{errors.database.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">{t('dataSources.username')}</Label>
              <Input id="username" {...register('username')} placeholder="用户名" />
              {errors.username && <p className="text-sm text-destructive">{errors.username.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('dataSources.password')}</Label>
              <Input id="password" type="password" {...register('password')} placeholder="密码" />
              {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="submit" disabled={isSubmitting || createDataSourceMutation.isPending}>
              {(isSubmitting || createDataSourceMutation.isPending) && (
                <LoadingSpinner size="sm" className="mr-2 text-current" />
              )}
              {t('common.save')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
