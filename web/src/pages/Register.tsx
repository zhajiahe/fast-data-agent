import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { emailSchema, passwordSchema, usernameSchema } from '@/lib/validations';

// 注册表单 Schema（扩展了昵称字段）
const registerFormSchema = z
  .object({
    username: usernameSchema,
    email: emailSchema,
    nickname: z.string().min(1, '昵称不能为空').max(30, '昵称最多 30 个字符'),
    password: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: '两次输入的密码不一致',
    path: ['confirmPassword'],
  });

type RegisterFormData = z.infer<typeof registerFormSchema>;

/**
 * 注册页面
 * 使用 React Hook Form + Zod 进行表单验证
 */
export const Register = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerFormSchema),
  });

  const onSubmit = async (_data: RegisterFormData) => {
    try {
      // TODO: 替换为真实的 API 调用，使用 _data 参数
      await new Promise((resolve) => setTimeout(resolve, 1000));

      toast({
        title: t('auth.register_success'),
        description: t('auth.register_success_desc'),
      });
      navigate('/login');
    } catch (err: any) {
      toast({
        title: t('auth.register_failed'),
        description: err.message || t('auth.register_failed_desc'),
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-slate-100 dark:from-emerald-950 dark:to-slate-900 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl text-center">{t('auth.register')}</CardTitle>
          <CardDescription className="text-center">{t('auth.register_subtitle')}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
            <div className="space-y-2">
              <Label htmlFor="username">{t('auth.username')}</Label>
              <Input
                id="username"
                placeholder={`${t('auth.enter_username')} (${t('auth.username_hint')})`}
                disabled={isSubmitting}
                {...register('username')}
                aria-invalid={!!errors.username}
              />
              {errors.username && <p className="text-sm text-destructive">{errors.username.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">{t('auth.email')}</Label>
              <Input
                id="email"
                type="email"
                placeholder={t('auth.enter_email')}
                disabled={isSubmitting}
                {...register('email')}
                aria-invalid={!!errors.email}
              />
              {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="nickname">{t('auth.nickname')}</Label>
              <Input
                id="nickname"
                placeholder={t('auth.enter_nickname')}
                disabled={isSubmitting}
                {...register('nickname')}
                aria-invalid={!!errors.nickname}
              />
              {errors.nickname && <p className="text-sm text-destructive">{errors.nickname.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t('auth.password')}</Label>
              <Input
                id="password"
                type="password"
                placeholder={`${t('auth.enter_password')} (${t('auth.password_hint')})`}
                disabled={isSubmitting}
                {...register('password')}
                aria-invalid={!!errors.password}
              />
              {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">{t('auth.confirm_password')}</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder={t('auth.enter_password_again')}
                disabled={isSubmitting}
                {...register('confirmPassword')}
                aria-invalid={!!errors.confirmPassword}
              />
              {errors.confirmPassword && <p className="text-sm text-destructive">{errors.confirmPassword.message}</p>}
            </div>

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? t('auth.registering') : t('auth.register')}
            </Button>

            <div className="text-center text-sm text-muted-foreground">
              <span>{t('auth.has_account')}</span>
              <Link to="/login" className="ml-1 text-primary hover:underline">
                {t('auth.login_now')}
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
