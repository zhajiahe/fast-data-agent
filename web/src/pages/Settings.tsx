import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeftIcon, KeyIcon, MoonIcon, SaveIcon, SunIcon, UserIcon } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { emailSchema, passwordSchema } from '@/lib/validations';
import { useThemeStore } from '@/stores/themeStore';

// 个人信息表单 Schema
const profileFormSchema = z.object({
  nickname: z.string().min(1, '昵称不能为空').max(30, '昵称最多 30 个字符'),
  email: emailSchema,
});

// 密码修改表单 Schema
const passwordFormSchema = z
  .object({
    oldPassword: passwordSchema,
    newPassword: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: '两次输入的密码不一致',
    path: ['confirmPassword'],
  });

type ProfileFormData = z.infer<typeof profileFormSchema>;
type PasswordFormData = z.infer<typeof passwordFormSchema>;

/**
 * 设置页面
 * 使用 React Hook Form + Zod 进行表单验证
 */
export const Settings = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const { theme, toggleTheme } = useThemeStore();

  // 个人信息表单
  const profileForm = useForm<ProfileFormData>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: { nickname: '', email: '' },
  });

  // 密码修改表单
  const passwordForm = useForm<PasswordFormData>({
    resolver: zodResolver(passwordFormSchema),
    defaultValues: { oldPassword: '', newPassword: '', confirmPassword: '' },
  });

  const handleSaveProfile = async (_data: ProfileFormData) => {
    // TODO: 替换为真实 API 调用，使用 _data 参数
    await new Promise((resolve) => setTimeout(resolve, 1000));
    toast({ title: t('settings.profile_saved'), description: t('settings.profile_saved_desc') });
  };

  const handleChangePassword = async (_data: PasswordFormData) => {
    // TODO: 替换为真实 API 调用，使用 _data 参数
    await new Promise((resolve) => setTimeout(resolve, 1000));
    toast({ title: t('settings.password_changed'), description: t('settings.password_changed_desc') });
    passwordForm.reset();
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 顶部导航栏 */}
      <div className="border-b">
        <div className="container flex h-16 items-center px-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/">
              <ArrowLeftIcon size={16} className="mr-2" />
              {t('settings.back_home')}
            </Link>
          </Button>
          <div className="ml-4 flex-1">
            <h1 className="text-2xl font-semibold tracking-tight">{t('settings.title')}</h1>
            <p className="text-sm text-muted-foreground">{t('settings.subtitle')}</p>
          </div>
        </div>
      </div>

      <div className="container max-w-4xl mx-auto py-6 px-4">
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
            <TabsTrigger value="profile" className="gap-2">
              <UserIcon size={16} />
              <span className="hidden sm:inline">{t('settings.profile')}</span>
            </TabsTrigger>
            <TabsTrigger value="security" className="gap-2">
              <KeyIcon size={16} />
              <span className="hidden sm:inline">{t('settings.security')}</span>
            </TabsTrigger>
          </TabsList>

          {/* 个人信息 */}
          <TabsContent value="profile" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>{t('settings.account_info')}</CardTitle>
                <CardDescription>{t('settings.account_info_desc')}</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={profileForm.handleSubmit(handleSaveProfile)} className="space-y-6">
                  <div className="grid gap-3">
                    <Label htmlFor="nickname">{t('settings.nickname')}</Label>
                    <Input
                      id="nickname"
                      placeholder={t('settings.enter_nickname')}
                      {...profileForm.register('nickname')}
                      aria-invalid={!!profileForm.formState.errors.nickname}
                    />
                    {profileForm.formState.errors.nickname && (
                      <p className="text-sm text-destructive">{profileForm.formState.errors.nickname.message}</p>
                    )}
                  </div>
                  <div className="grid gap-3">
                    <Label htmlFor="email">{t('settings.email')}</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder={t('settings.enter_email')}
                      {...profileForm.register('email')}
                      aria-invalid={!!profileForm.formState.errors.email}
                    />
                    {profileForm.formState.errors.email && (
                      <p className="text-sm text-destructive">{profileForm.formState.errors.email.message}</p>
                    )}
                  </div>
                  <Separator />
                  <div className="flex justify-end">
                    <Button type="submit" disabled={profileForm.formState.isSubmitting}>
                      <SaveIcon size={16} className="mr-2" />
                      {profileForm.formState.isSubmitting ? t('common.saving') : t('common.save')}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {/* 主题设置 */}
            <Card>
              <CardHeader>
                <CardTitle>{t('settings.appearance')}</CardTitle>
                <CardDescription>{t('settings.appearance_desc')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {theme === 'dark' ? <MoonIcon size={20} /> : <SunIcon size={20} />}
                    <div>
                      <Label>{t('settings.dark_mode')}</Label>
                      <p className="text-sm text-muted-foreground">{t('settings.dark_mode_desc')}</p>
                    </div>
                  </div>
                  <Switch checked={theme === 'dark'} onCheckedChange={toggleTheme} />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 安全设置 */}
          <TabsContent value="security" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>{t('settings.change_password')}</CardTitle>
                <CardDescription>{t('settings.change_password_desc')}</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={passwordForm.handleSubmit(handleChangePassword)} className="space-y-6">
                  <div className="grid gap-3">
                    <Label htmlFor="oldPassword">{t('settings.current_password')}</Label>
                    <Input
                      id="oldPassword"
                      type="password"
                      placeholder={t('settings.enter_current_password')}
                      {...passwordForm.register('oldPassword')}
                      aria-invalid={!!passwordForm.formState.errors.oldPassword}
                    />
                    {passwordForm.formState.errors.oldPassword && (
                      <p className="text-sm text-destructive">{passwordForm.formState.errors.oldPassword.message}</p>
                    )}
                  </div>
                  <div className="grid gap-3">
                    <Label htmlFor="newPassword">{t('settings.new_password')}</Label>
                    <Input
                      id="newPassword"
                      type="password"
                      placeholder={t('settings.at_least_6_chars')}
                      {...passwordForm.register('newPassword')}
                      aria-invalid={!!passwordForm.formState.errors.newPassword}
                    />
                    {passwordForm.formState.errors.newPassword && (
                      <p className="text-sm text-destructive">{passwordForm.formState.errors.newPassword.message}</p>
                    )}
                  </div>
                  <div className="grid gap-3">
                    <Label htmlFor="confirmPassword">{t('settings.confirm_password')}</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      placeholder={t('settings.enter_new_password_again')}
                      {...passwordForm.register('confirmPassword')}
                      aria-invalid={!!passwordForm.formState.errors.confirmPassword}
                    />
                    {passwordForm.formState.errors.confirmPassword && (
                      <p className="text-sm text-destructive">
                        {passwordForm.formState.errors.confirmPassword.message}
                      </p>
                    )}
                  </div>
                  <Separator />
                  <div className="flex justify-end">
                    <Button type="submit" disabled={passwordForm.formState.isSubmitting}>
                      <KeyIcon size={16} className="mr-2" />
                      {passwordForm.formState.isSubmitting ? t('common.saving') : t('settings.change_password')}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};
