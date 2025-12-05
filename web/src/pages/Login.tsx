import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2 } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useLogin } from '@/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { type LoginFormData, loginSchema } from '@/lib/validations';
import { useAuthStore } from '@/stores/authStore';

/**
 * 登录页面
 */
export const Login = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((state) => state.setAuth);
  const { toast } = useToast();

  // 获取重定向路径
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // 使用生成的 API hook
  const loginMutation = useLogin();

  const onSubmit = async (data: LoginFormData) => {
    loginMutation.mutate(data, {
      onSuccess: (response) => {
        const { id, nickname, access_token, refresh_token } = response.data.data!;
        setAuth(
          {
            id: String(id),
            username: '', // 后端不返回 username，暂时留空
            nickname: nickname,
          },
          access_token,
          refresh_token
        );

        toast({
          title: t('auth.login_success'),
          description: t('auth.login_success_desc', { username: nickname }),
        });

        navigate(from, { replace: true });
      },
      onError: (error: Error) => {
        toast({
          title: t('auth.login_failed'),
          description: error.message || t('auth.login_failed_desc'),
          variant: 'destructive',
        });
      },
    });
  };

  return (
    <div className="min-h-screen flex">
      {/* 左侧装饰区域 */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-violet-600 via-purple-600 to-indigo-700 p-12 flex-col justify-between relative overflow-hidden">
        {/* 背景装饰 */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-20 left-20 w-72 h-72 bg-white rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-purple-300 rounded-full blur-3xl" />
        </div>

        {/* Logo */}
        <div className="relative">
          <div className="flex items-center gap-3">
            <img src="/data_agent_logo.png" alt="Logo" className="h-10 w-10 rounded-xl" />
            <span className="text-2xl font-bold text-white">Fast Data Agent</span>
          </div>
        </div>

        {/* 主要内容 */}
        <div className="relative">
          <h1 className="text-4xl font-bold text-white mb-4">{t('auth.slogan_title')}</h1>
          <p className="text-lg text-white/80 max-w-md">{t('auth.slogan_desc')}</p>
        </div>

        {/* 底部 */}
        <div className="relative text-white/60 text-sm">© 2024 Fast Data Agent. All rights reserved.</div>
      </div>

      {/* 右侧登录表单 */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <Card className="w-full max-w-md border-0 shadow-none lg:shadow lg:border">
          <CardHeader className="space-y-1 text-center">
            {/* 移动端 Logo */}
            <div className="lg:hidden flex justify-center mb-4">
              <img src="/data_agent_logo.png" alt="Logo" className="h-12 w-12 rounded-xl" />
            </div>
            <CardTitle className="text-2xl">{t('auth.login')}</CardTitle>
            <CardDescription>{t('auth.login_subtitle')}</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
              <div className="space-y-2">
                <Label htmlFor="username">{t('auth.username')}</Label>
                <Input
                  id="username"
                  placeholder={t('auth.enter_username')}
                  autoComplete="username"
                  disabled={isSubmitting || loginMutation.isPending}
                  {...register('username')}
                  aria-invalid={!!errors.username}
                />
                {errors.username && <p className="text-sm text-destructive">{errors.username.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">{t('auth.password')}</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder={t('auth.enter_password')}
                  autoComplete="current-password"
                  disabled={isSubmitting || loginMutation.isPending}
                  {...register('password')}
                  aria-invalid={!!errors.password}
                />
                {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
              </div>

              <Button type="submit" className="w-full" disabled={isSubmitting || loginMutation.isPending}>
                {(isSubmitting || loginMutation.isPending) ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {t('auth.logging_in')}
                  </>
                ) : (
                  t('auth.login')
                )}
              </Button>

              <div className="text-center text-sm text-muted-foreground">
                <span>{t('auth.no_account')}</span>
                <Link to="/register" className="ml-1 text-primary hover:underline">
                  {t('auth.register_now')}
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
