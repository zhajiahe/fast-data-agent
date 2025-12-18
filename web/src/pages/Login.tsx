import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useLogin } from '@/api';
import { AuthLayout } from '@/components/auth/AuthLayout';
import { LoadingSpinner } from '@/components/common';
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

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const loginMutation = useLogin();
  const isLoading = isSubmitting || loginMutation.isPending;

  const onSubmit = async (data: LoginFormData) => {
    loginMutation.mutate(data, {
      onSuccess: (response) => {
        const responseData = response.data.data;
        if (!responseData) return;
        const { id, username, nickname, email, is_active, is_superuser, access_token, refresh_token } = responseData;
        setAuth(
          {
            id: String(id),
            username: username ?? '',
            nickname: nickname ?? undefined,
            email: email ?? undefined,
            is_active: is_active ?? true,
            is_superuser: is_superuser ?? false,
          },
          access_token,
          refresh_token
        );
        toast({ title: t('auth.login_success'), description: t('auth.login_success_desc', { username: nickname }) });
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
    <AuthLayout title={t('auth.slogan_title')} subtitle={t('auth.slogan_desc')}>
      <Card className="w-full max-w-md border-0 shadow-none lg:shadow lg:border">
        <CardHeader className="space-y-1 text-center">
          {/* 移动端 Logo */}
          <div className="lg:hidden flex justify-center mb-4">
            <img src={`${import.meta.env.BASE_URL}data_agent_logo.png`} alt="Logo" className="h-12 w-auto rounded-xl" />
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
                disabled={isLoading}
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
                disabled={isLoading}
                {...register('password')}
                aria-invalid={!!errors.password}
              />
              {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2 text-current" />
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
    </AuthLayout>
  );
};
