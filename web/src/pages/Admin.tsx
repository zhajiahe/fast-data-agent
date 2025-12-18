import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  Ban,
  CheckCircle,
  Database,
  Eye,
  FileText,
  FolderOpen,
  Key,
  MessageSquare,
  MoreHorizontal,
  RefreshCw,
  Search,
  Shield,
  ShieldOff,
  Trash2,
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
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
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

// 用户资源统计
interface UserResourceStats {
  user_id: string;
  username: string;
  nickname: string;
  sessions_count: number;
  messages_count: number;
  data_sources_count: number;
  raw_data_count: number;
  connections_count: number;
  files_count: number;
  total_file_size: number;
}

// 用户资源详情
interface UserResourceDetail {
  user: UserItem;
  resources: UserResourceStats;
  sessions: Array<{
    id: string;
    name: string;
    status: string;
    message_count: number;
    create_time: string;
  }>;
  data_sources: Array<{
    id: string;
    name: string;
    description: string;
    create_time: string;
  }>;
  connections: Array<{
    id: string;
    name: string;
    db_type: string;
    host: string;
    database: string;
    create_time: string;
  }>;
  files: Array<{
    id: string;
    original_name: string;
    file_type: string;
    file_size: number;
    status: string;
    create_time: string;
  }>;
}

// 批量删除结果
interface BatchDeleteResult {
  success_count: number;
  failed_count: number;
  skipped_count: number;
  details: Array<{
    user_id: string;
    username?: string;
    status: string;
    reason?: string;
    deleted_resources?: {
      sessions: number;
      messages: number;
      data_sources: number;
      raw_data: number;
      connections: number;
      files: number;
      minio_files: number;
      sandbox_cleaned: boolean;
    };
  }>;
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

  getUserResources: async (userId: string): Promise<UserResourceDetail> => {
    const token = storage.getToken();
    const res = await fetch(`${API_BASE}/admin/users/${userId}/resources`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.msg);
    return data.data;
  },

  batchDeleteUsers: async (userIds: string[]): Promise<BatchDeleteResult> => {
    const token = storage.getToken();
    const res = await fetch(`${API_BASE}/admin/users/batch-delete`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_ids: userIds }),
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.msg);
    return data.data;
  },

  cascadeDeleteUser: async (userId: string) => {
    const token = storage.getToken();
    const res = await fetch(`${API_BASE}/admin/users/${userId}/cascade`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.msg);
    return data.data;
  },
};

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
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

// 用户资源详情对话框
const UserResourceDialog = ({
  userId,
  open,
  onClose,
}: {
  userId: string | null;
  open: boolean;
  onClose: () => void;
}) => {
  const { data, isLoading } = useQuery({
    queryKey: ['user-resources', userId],
    queryFn: () => (userId ? adminApi.getUserResources(userId) : Promise.reject()),
    enabled: !!userId && open,
  });

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5" />
            用户资源详情
          </DialogTitle>
          {data && (
            <DialogDescription>
              查看 <strong>{data.user.nickname || data.user.username}</strong> 的所有资源
            </DialogDescription>
          )}
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-4 py-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : data ? (
          <div className="space-y-6 py-4">
            {/* 资源统计概览 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950 text-center">
                <div className="text-2xl font-bold text-blue-600">{data.resources.sessions_count}</div>
                <div className="text-xs text-muted-foreground">会话</div>
              </div>
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-950 text-center">
                <div className="text-2xl font-bold text-green-600">{data.resources.messages_count}</div>
                <div className="text-xs text-muted-foreground">消息</div>
              </div>
              <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-950 text-center">
                <div className="text-2xl font-bold text-purple-600">{data.resources.data_sources_count}</div>
                <div className="text-xs text-muted-foreground">数据源</div>
              </div>
              <div className="p-3 rounded-lg bg-orange-50 dark:bg-orange-950 text-center">
                <div className="text-2xl font-bold text-orange-600">{data.resources.files_count}</div>
                <div className="text-xs text-muted-foreground">文件 ({formatFileSize(data.resources.total_file_size)})</div>
              </div>
            </div>

            {/* 详细列表 */}
            <Tabs defaultValue="sessions" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="sessions">会话 ({data.sessions.length})</TabsTrigger>
                <TabsTrigger value="data_sources">数据源 ({data.data_sources.length})</TabsTrigger>
                <TabsTrigger value="connections">连接 ({data.connections.length})</TabsTrigger>
                <TabsTrigger value="files">文件 ({data.files.length})</TabsTrigger>
              </TabsList>

              <TabsContent value="sessions" className="mt-4">
                <ScrollArea className="h-[200px]">
                  {data.sessions.length === 0 ? (
                    <p className="text-center text-muted-foreground py-4">暂无会话</p>
                  ) : (
                    <div className="space-y-2">
                      {data.sessions.map((s) => (
                        <div key={s.id} className="flex justify-between items-center p-2 rounded border text-sm">
                          <span className="font-medium truncate flex-1">{s.name}</span>
                          <Badge variant="outline" className="ml-2">{s.message_count} 条消息</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              <TabsContent value="data_sources" className="mt-4">
                <ScrollArea className="h-[200px]">
                  {data.data_sources.length === 0 ? (
                    <p className="text-center text-muted-foreground py-4">暂无数据源</p>
                  ) : (
                    <div className="space-y-2">
                      {data.data_sources.map((ds) => (
                        <div key={ds.id} className="flex justify-between items-center p-2 rounded border text-sm">
                          <span className="font-medium truncate flex-1">{ds.name}</span>
                          <span className="text-xs text-muted-foreground">{ds.create_time?.split('T')[0]}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              <TabsContent value="connections" className="mt-4">
                <ScrollArea className="h-[200px]">
                  {data.connections.length === 0 ? (
                    <p className="text-center text-muted-foreground py-4">暂无数据库连接</p>
                  ) : (
                    <div className="space-y-2">
                      {data.connections.map((c) => (
                        <div key={c.id} className="flex justify-between items-center p-2 rounded border text-sm">
                          <div className="flex-1">
                            <span className="font-medium">{c.name}</span>
                            <span className="text-muted-foreground ml-2">({c.db_type})</span>
                          </div>
                          <span className="text-xs text-muted-foreground truncate max-w-[150px]">{c.host}/{c.database}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              <TabsContent value="files" className="mt-4">
                <ScrollArea className="h-[200px]">
                  {data.files.length === 0 ? (
                    <p className="text-center text-muted-foreground py-4">暂无上传文件</p>
                  ) : (
                    <div className="space-y-2">
                      {data.files.map((f) => (
                        <div key={f.id} className="flex justify-between items-center p-2 rounded border text-sm">
                          <span className="font-medium truncate flex-1">{f.original_name}</span>
                          <span className="text-xs text-muted-foreground">{formatFileSize(f.file_size)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>
            </Tabs>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
};

// 批量删除确认对话框
const BatchDeleteDialog = ({
  selectedUsers,
  open,
  onClose,
  onConfirm,
  isPending,
  result,
}: {
  selectedUsers: UserItem[];
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isPending: boolean;
  result: BatchDeleteResult | null;
}) => {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            确认批量删除
          </DialogTitle>
          <DialogDescription>
            此操作将删除选中用户及其所有关联资源，包括会话、消息、数据源、文件等。此操作不可撤销！
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {result ? (
            // 显示删除结果
            <div className="space-y-4">
              <div className="flex gap-4 justify-center">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{result.success_count}</div>
                  <div className="text-xs text-muted-foreground">成功</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{result.failed_count}</div>
                  <div className="text-xs text-muted-foreground">失败</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-600">{result.skipped_count}</div>
                  <div className="text-xs text-muted-foreground">跳过</div>
                </div>
              </div>
              <ScrollArea className="h-[200px] border rounded p-2">
                {result.details.map((d, i) => (
                  <div key={i} className="flex justify-between items-center py-1 text-sm border-b last:border-0">
                    <span>{d.username || d.user_id}</span>
                    <Badge variant={d.status === 'success' ? 'default' : d.status === 'skipped' ? 'secondary' : 'destructive'}>
                      {d.status === 'success' ? '已删除' : d.status === 'skipped' ? '跳过' : '失败'}
                    </Badge>
                  </div>
                ))}
              </ScrollArea>
            </div>
          ) : (
            // 显示待删除用户列表
            <>
              <p className="text-sm mb-3">即将删除以下 <strong>{selectedUsers.length}</strong> 个用户：</p>
              <ScrollArea className="h-[200px] border rounded p-2">
                {selectedUsers.map((user) => (
                  <div key={user.id} className="flex items-center gap-2 py-1 border-b last:border-0">
                    <Avatar className="h-6 w-6">
                      <AvatarFallback className="text-xs">{user.username.charAt(0).toUpperCase()}</AvatarFallback>
                    </Avatar>
                    <span className="text-sm">{user.nickname || user.username}</span>
                    <span className="text-xs text-muted-foreground">({user.email})</span>
                  </div>
                ))}
              </ScrollArea>
            </>
          )}
        </div>

        <DialogFooter>
          {result ? (
            <Button onClick={onClose}>关闭</Button>
          ) : (
            <>
              <Button variant="outline" onClick={onClose} disabled={isPending}>
                取消
              </Button>
              <Button variant="destructive" onClick={onConfirm} disabled={isPending}>
                {isPending ? '删除中...' : `确认删除 ${selectedUsers.length} 个用户`}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// 用户列表组件
const UserList = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [searchKeyword, setSearchKeyword] = useState('');
  const [resetPasswordUser, setResetPasswordUser] = useState<UserItem | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(new Set());
  const [viewResourcesUserId, setViewResourcesUserId] = useState<string | null>(null);
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false);
  const [batchDeleteResult, setBatchDeleteResult] = useState<BatchDeleteResult | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const pageSize = 20;

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin-users', searchKeyword, pageNum],
    queryFn: () => adminApi.getUsers({ page_num: pageNum, page_size: pageSize, keyword: searchKeyword || undefined }),
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

  const batchDeleteMutation = useMutation({
    mutationFn: (userIds: string[]) => adminApi.batchDeleteUsers(userIds),
    onSuccess: (result) => {
      setBatchDeleteResult(result);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      setSelectedUserIds(new Set());
      toast({
        title: '批量删除完成',
        description: `成功: ${result.success_count}, 失败: ${result.failed_count}`,
      });
    },
    onError: (err: Error) => {
      toast({ title: '批量删除失败', description: err.message, variant: 'destructive' });
    },
  });

  const users: UserItem[] = data?.items || [];
  const totalUsers = data?.total || 0;
  const totalPages = Math.ceil(totalUsers / pageSize);

  // 切换单个用户选中状态
  const toggleUserSelection = (userId: string) => {
    const newSelection = new Set(selectedUserIds);
    if (newSelection.has(userId)) {
      newSelection.delete(userId);
    } else {
      newSelection.add(userId);
    }
    setSelectedUserIds(newSelection);
  };

  // 切换全选
  const toggleSelectAll = () => {
    if (selectedUserIds.size === users.length) {
      setSelectedUserIds(new Set());
    } else {
      setSelectedUserIds(new Set(users.map((u) => u.id)));
    }
  };

  // 获取选中的用户对象
  const selectedUsers = users.filter((u) => selectedUserIds.has(u.id));

  // 处理批量删除
  const handleBatchDelete = () => {
    setBatchDeleteResult(null);
    setBatchDeleteOpen(true);
  };

  const confirmBatchDelete = () => {
    batchDeleteMutation.mutate(Array.from(selectedUserIds));
  };

  const closeBatchDeleteDialog = () => {
    setBatchDeleteOpen(false);
    setBatchDeleteResult(null);
  };

  return (
    <div className="space-y-4">
      {/* 搜索栏和操作按钮 */}
      <div className="flex gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索用户名、邮箱或昵称..."
            className="pl-10"
            value={searchKeyword}
            onChange={(e) => {
              setSearchKeyword(e.target.value);
              setPageNum(1); // Reset to first page on search
            }}
          />
        </div>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
        {selectedUserIds.size > 0 && (
          <Button variant="destructive" onClick={handleBatchDelete}>
            <Trash2 className="h-4 w-4 mr-2" />
            删除选中 ({selectedUserIds.size})
          </Button>
        )}
      </div>

      {/* 用户表格 */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="w-12">
                <Checkbox
                  checked={selectedUserIds.size === users.length && users.length > 0}
                  onCheckedChange={toggleSelectAll}
                />
              </TableHead>
              <TableHead>用户</TableHead>
              <TableHead>邮箱</TableHead>
              <TableHead className="text-center">状态</TableHead>
              <TableHead className="text-center">角色</TableHead>
              <TableHead className="text-center">注册时间</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={7}>
                    <Skeleton className="h-12 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                  <Users className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>暂无用户</p>
                </TableCell>
              </TableRow>
            ) : (
              users.map((user) => (
                <TableRow
                  key={user.id}
                  className={selectedUserIds.has(user.id) ? 'bg-primary/5' : ''}
                >
                  <TableCell>
                    <Checkbox
                      checked={selectedUserIds.has(user.id)}
                      onCheckedChange={() => toggleUserSelection(user.id)}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-primary/10 text-primary text-sm">
                          {user.username.charAt(0).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <span className="font-medium">{user.nickname || user.username}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{user.email}</TableCell>
                  <TableCell className="text-center">
                    {user.is_active ? (
                      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        正常
                      </Badge>
                    ) : (
                      <Badge variant="destructive">
                        <Ban className="h-3 w-3 mr-1" />
                        禁用
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    {user.is_superuser ? (
                      <Badge className="bg-amber-100 text-amber-800 border-amber-200">
                        <Shield className="h-3 w-3 mr-1" />
                        管理员
                      </Badge>
                    ) : (
                      <Badge variant="secondary">普通用户</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-center text-sm text-muted-foreground">
                    {user.create_time ? new Date(user.create_time).toLocaleDateString() : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setViewResourcesUserId(user.id)}
                        title="查看资源"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setViewResourcesUserId(user.id)}>
                            <Eye className="h-4 w-4 mr-2" />
                            查看资源
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
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
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => {
                              setSelectedUserIds(new Set([user.id]));
                              handleBatchDelete();
                            }}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            删除用户
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页控制 */}
      <div className="flex items-center justify-between py-4">
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">
            共 <span className="font-medium text-foreground">{totalUsers}</span> 个用户
          </span>
          {selectedUserIds.size > 0 && (
            <Badge variant="secondary">
              已选中 {selectedUserIds.size} 个
            </Badge>
          )}
        </div>
        {totalPages > 1 && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageNum((p) => Math.max(1, p - 1))}
              disabled={pageNum <= 1}
            >
              上一页
            </Button>
            <span className="text-sm px-2">
              {pageNum} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPageNum((p) => Math.min(totalPages, p + 1))}
              disabled={pageNum >= totalPages}
            >
              下一页
            </Button>
          </div>
        )}
      </div>

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

      {/* 用户资源详情对话框 */}
      <UserResourceDialog
        userId={viewResourcesUserId}
        open={!!viewResourcesUserId}
        onClose={() => setViewResourcesUserId(null)}
      />

      {/* 批量删除确认对话框 */}
      <BatchDeleteDialog
        selectedUsers={selectedUsers}
        open={batchDeleteOpen}
        onClose={closeBatchDeleteDialog}
        onConfirm={confirmBatchDelete}
        isPending={batchDeleteMutation.isPending}
        result={batchDeleteResult}
      />
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

