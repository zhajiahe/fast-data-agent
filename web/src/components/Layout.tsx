import {
  Check,
  Database,
  Languages,
  LayoutDashboardIcon,
  LogOutIcon,
  MessageSquare,
  MoonIcon,
  SettingsIcon,
  SunIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';
import { useThemeStore } from '@/stores/themeStore';

interface LayoutProps {
  children: React.ReactNode;
}

const languages = [
  { code: 'en', label: 'English' },
  { code: 'zh', label: '中文' },
];

/**
 * 应用主布局组件
 */
export const Layout = ({ children }: LayoutProps) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useThemeStore();
  const { user, logout } = useAuthStore();
  const { t, i18n } = useTranslation();

  const navItems = [
    { path: '/', labelKey: 'nav.dashboard', icon: LayoutDashboardIcon },
    { path: '/sessions', labelKey: 'nav.sessions', icon: MessageSquare },
    { path: '/data-sources', labelKey: 'nav.dataSources', icon: Database },
  ];

  const isActive = (path: string) => location.pathname === path;

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  const getCurrentLanguage = () => {
    return i18n.language.split('-')[0];
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 顶部导航栏 */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center px-4">
          {/* Logo */}
          <Link to="/" className="mr-6 flex items-center space-x-2">
            <img src={`${import.meta.env.BASE_URL}data_agent_logo.png`} alt="Logo" className="h-8 w-8 rounded-lg" />
            <span className="hidden font-bold sm:inline-block bg-gradient-to-r from-violet-600 to-purple-600 bg-clip-text text-transparent">
              Fast Data Agent
            </span>
          </Link>

          {/* 主导航 */}
          <nav className="flex items-center space-x-1 flex-1">
            {navItems.map((item) => (
              <Button
                key={item.path}
                variant={isActive(item.path) ? 'secondary' : 'ghost'}
                size="sm"
                asChild
                className={cn('gap-2', isActive(item.path) && 'bg-muted')}
              >
                <Link to={item.path}>
                  <item.icon className="h-4 w-4" />
                  <span className="hidden md:inline">{t(item.labelKey)}</span>
                </Link>
              </Button>
            ))}
          </nav>

          {/* 右侧操作 */}
          <div className="flex items-center gap-2">
            {/* 语言切换 */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Languages className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {languages.map((lang) => (
                  <DropdownMenuItem
                    key={lang.code}
                    onClick={() => changeLanguage(lang.code)}
                    className="cursor-pointer"
                  >
                    <Check
                      className={cn('mr-2 h-4 w-4', getCurrentLanguage() === lang.code ? 'opacity-100' : 'opacity-0')}
                    />
                    {lang.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* 主题切换 */}
            <Button variant="ghost" size="icon" onClick={toggleTheme}>
              {theme === 'dark' ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
            </Button>

            {/* 用户菜单 */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="relative">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                      {user?.username?.charAt(0).toUpperCase() || 'U'}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5">
                  <p className="font-medium text-sm">{user?.nickname || user?.username}</p>
                  <p className="text-xs text-muted-foreground">{user?.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild className="cursor-pointer">
                  <Link to="/settings">
                    <SettingsIcon className="h-4 w-4 mr-2" />
                    {t('nav.settings')}
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-destructive">
                  <LogOutIcon className="h-4 w-4 mr-2" />
                  {t('auth.logout')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* 页面内容 */}
      <main>{children}</main>
    </div>
  );
};
