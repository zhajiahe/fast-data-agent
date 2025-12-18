import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  Ban,
  CheckCircle,
  Database,
  FileText,
  Key,
  MessageSquare,
  MoreHorizontal,
  RefreshCw,
  Search,
  Shield,
  ShieldOff,
  UserCheck,
  UserCog,
  Users,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { storage } from '@/utils/storage';

// API 基础 URL
const API_BASE = '/api/v1';

// 系统统计类型
interface SystemStats {
  total_users: number;
  active_users: number;
  total_sessions: number;
  total_messages: number;
  total_data_sources: number;
  total_raw_data: number;
  total_connections: number;
  total_files: number;
  users_today: number;
  sessions_today: number;
  messages_today: number;
}

// 用户类型
interface UserItem {
  id: string;
  username: string;
  email: string;
  nickname: string;
  is_active: boolean;
  is_superuser: boolean;
  create_time: string;
  update_time: string;
}

// API 封装
const adminApi = {
  getStats: async (): Promise<SystemStats> => {
    const token = storage.getToken();
    const res = await fetch(`${API_BASE}/admin/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.msg);
    return data.data;
  },

  getUsers: async (params: { page_num: number; page_size: number; keyword?: string }) => {
    const token = storage.getToken();
    const query = new URLSearchParams({
      page_num: String(params.page_num),
      page_size: String(params.page_size),
      ...(params.keyword && { keyword: params.keyword }),
    });
    const res = await fetch(`${API_BASE}/users?${query}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.msg);
    return data.data;
  },

  toggleUserStatus: async (userId: string, isActive: boolean) => {
    const token = storage.getToken();
    const res = await fetch(`${API_BASE}/admin/users/${userId}/toggle`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ is_active: isActive }),
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.msg);
    return data.data;
  },

  toggleUserRole: async (userId: string, isSuperuser: boolean) => {
    const token = storage.getToken();
    const res = await fetch(`${API_BASE}/admin/users/${userId}/role`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ is_superuser: isSuperuser }),
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.msg);
    return data.data;
  },

  resetPassword: async (userId: string, newPassword: string) => {
    const token = storage.getToken();
    const res = await fetch(`${API_BASE}/admin/users/${userId}/reset-password`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ new_password: newPassword }),
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.msg);
    return data;
  },
};

// 统计卡片组件
const StatCard = ({
  title,
  value,
  icon: Icon,
  today,
  color,
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  today?: number;
  color: string;
}) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      <Icon className={`h-4 w-4 ${color}`} />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value.toLocaleString()}</div>
      {today !== undefined && (
        <p className="text-xs text-muted-foreground mt-1">今日新增 +{today}</p>
      )}
    </CardContent>
  </Card>
);

// 用户列表组件
const UserList = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [resetPasswordUser, setResetPasswordUser] = useState<UserItem | null>(null);
  const [newPassword, setNewPassword] = useState('');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin-users', searchKeyword],
    queryFn: () => adminApi.getUsers({ page_num: 1, page_size: 100, keyword: searchKeyword || undefined }),
  });

  const toggleStatusMutation = useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      adminApi.toggleUserStatus(userId, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast({ title: '操作成功' });
    },
    onError: (err: Error) => {
      toast({ title: '操作失败', description: err.message, variant: 'destructive' });
    },
  });

  const toggleRoleMutation = useMutation({
    mutationFn: ({ userId, isSuperuser }: { userId: string; isSuperuser: boolean }) =>
      adminApi.toggleUserRole(userId, isSuperuser),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast({ title: '操作成功' });
    },
    onError: (err: Error) => {
      toast({ title: '操作失败', description: err.message, variant: 'destructive' });
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({ userId, password }: { userId: string; password: string }) =>
      adminApi.resetPassword(userId, password),
    onSuccess: () => {
      setResetPasswordUser(null);
      setNewPassword('');
      toast({ title: '密码重置成功' });
    },
    onError: (err: Error) => {
      toast({ title: '重置失败', description: err.message, variant: 'destructive' });
    },
  });

  const users: UserItem[] = data?.items || [];

  return (
    <div className="space-y-4">
      {/* 搜索栏 */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索用户名、邮箱或昵称..."
            className="pl-10"
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
          />
        </div>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* 用户列表 */}
      <ScrollArea className="h-[500px]">
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Users className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>暂无用户</p>
          </div>
        ) : (
          <div className="space-y-2">
            {users.map((user) => (
              <div
                key={user.id}
                className="flex items-center justify-between p-4 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-primary/10 text-primary">
                      {user.username.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{user.nickname || user.username}</span>
                      {user.is_superuser && (
                        <Badge variant="default" className="text-xs">
                          <Shield className="h-3 w-3 mr-1" />
                          管理员
                        </Badge>
                      )}
                      {!user.is_active && (
                        <Badge variant="destructive" className="text-xs">
                          已禁用
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">{user.email}</div>
                  </div>
                </div>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => toggleStatusMutation.mutate({ userId: user.id, isActive: !user.is_active })}
                    >
                      {user.is_active ? (
                        <>
                          <Ban className="h-4 w-4 mr-2" />
                          禁用用户
                        </>
                      ) : (
                        <>
                          <CheckCircle className="h-4 w-4 mr-2" />
                          启用用户
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => toggleRoleMutation.mutate({ userId: user.id, isSuperuser: !user.is_superuser })}
                    >
                      {user.is_superuser ? (
                        <>
                          <ShieldOff className="h-4 w-4 mr-2" />
                          取消管理员
                        </>
                      ) : (
                        <>
                          <Shield className="h-4 w-4 mr-2" />
                          设为管理员
                        </>
                      )}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => setResetPasswordUser(user)}>
                      <Key className="h-4 w-4 mr-2" />
                      重置密码
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* 重置密码对话框 */}
      <Dialog open={!!resetPasswordUser} onOpenChange={() => setResetPasswordUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重置密码</DialogTitle>
            <DialogDescription>
              为用户 <strong>{resetPasswordUser?.nickname || resetPasswordUser?.username}</strong> 设置新密码
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="new-password">新密码</Label>
            <Input
              id="new-password"
              type="password"
              placeholder="输入新密码（至少 6 位）"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResetPasswordUser(null)}>
              取消
            </Button>
            <Button
              onClick={() =>
                resetPasswordUser && resetPasswordMutation.mutate({ userId: resetPasswordUser.id, password: newPassword })
              }
              disabled={newPassword.length < 6 || resetPasswordMutation.isPending}
            >
              {resetPasswordMutation.isPending ? '重置中...' : '确认重置'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

/**
 * 管理后台页面
 */
export const Admin = () => {
  const { t } = useTranslation();

  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.getStats,
  });

  return (
    <div className="container py-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <UserCog className="h-6 w-6 text-primary" />
            管理后台
          </h1>
          <p className="text-muted-foreground">系统管理与用户管理</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetchStats()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          刷新数据
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statsLoading ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <Skeleton className="h-4 w-24" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-16" />
                </CardContent>
              </Card>
            ))}
          </>
        ) : stats ? (
          <>
            <StatCard
              title="总用户数"
              value={stats.total_users}
              icon={Users}
              today={stats.users_today}
              color="text-blue-500"
            />
            <StatCard
              title="活跃用户"
              value={stats.active_users}
              icon={UserCheck}
              color="text-green-500"
            />
            <StatCard
              title="分析会话"
              value={stats.total_sessions}
              icon={MessageSquare}
              today={stats.sessions_today}
              color="text-purple-500"
            />
            <StatCard
              title="总消息数"
              value={stats.total_messages}
              icon={Activity}
              today={stats.messages_today}
              color="text-orange-500"
            />
          </>
        ) : null}
      </div>

      {/* 更多统计 */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <StatCard title="数据源" value={stats.total_data_sources} icon={Database} color="text-teal-500" />
          <StatCard title="数据对象" value={stats.total_raw_data} icon={FileText} color="text-indigo-500" />
          <StatCard title="数据库连接" value={stats.total_connections} icon={Database} color="text-pink-500" />
          <StatCard title="上传文件" value={stats.total_files} icon={FileText} color="text-cyan-500" />
        </div>
      )}

      {/* 用户管理 Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>用户管理</CardTitle>
          <CardDescription>管理系统用户，包括激活/禁用、角色分配、密码重置等</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="users">
            <TabsList>
              <TabsTrigger value="users">用户列表</TabsTrigger>
            </TabsList>
            <TabsContent value="users" className="mt-4">
              <UserList />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

