import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useDbConnections, useDbTableSchema, useDbTables, useFiles } from '@/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';

interface DataSourceWizardDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * 数据源向导（预览版）
 * - 文件：列出已上传文件，支持勾选列
 * - 数据库：选择连接 -> 选择表 -> 查看列
 * - 提交功能暂未打通，这里先做浏览与勾选体验
 */
export const DataSourceWizardDialog = ({ open, onOpenChange }: DataSourceWizardDialogProps) => {
  const { t } = useTranslation();
  const [mode, setMode] = useState<'file' | 'database'>('file');
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);
  const [selectedTable, setSelectedTable] = useState<{ schema?: string | null; name: string } | null>(null);
  const [selectedColumns, setSelectedColumns] = useState<Set<string>>(new Set());

  // 文件数据
  const { data: filesResp } = useFiles();
  const files = filesResp?.data.data?.items || [];
  const selectedFile = files.find((f) => f.id === selectedFileId);
  const fileColumns = (selectedFile?.columns_info as { name?: string; dtype?: string }[] | undefined) || [];

  // 数据库连接与表
  const { data: connResp } = useDbConnections();
  const connections = connResp?.data.data?.items || [];
  const { data: tablesResp } = useDbTables(selectedConnectionId || undefined);
  const tables = tablesResp?.data.data?.tables || [];

  // 列信息（数据库表）
  const { data: schemaResp } = useDbTableSchema(
    selectedConnectionId || undefined,
    selectedTable
      ? {
          schema_name: selectedTable.schema || undefined,
          table_name: selectedTable.name,
        }
      : undefined
  );
  const tableColumns = schemaResp?.data.data?.columns || [];

  const _currentColumns = useMemo(() => {
    if (mode === 'file') return fileColumns.map((c) => ({ name: c.name || '', type: c.dtype || '' }));
    return tableColumns.map((c) => ({ name: c.name || '', type: c.data_type || '' }));
  }, [fileColumns, tableColumns, mode]);

  const toggleColumn = (name: string) => {
    setSelectedColumns((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleClose = () => {
    setSelectedFileId(null);
    setSelectedConnectionId(null);
    setSelectedTable(null);
    setSelectedColumns(new Set());
    setMode('file');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[860px]">
        <DialogHeader>
          <DialogTitle>{t('dataSources.dataSourceWizard') || '数据源向导（预览）'}</DialogTitle>
          <DialogDescription>
            {t('dataSources.dataSourceWizardDesc') ||
              '选择文件或数据库表，预览列信息并勾选需要的列。后续提交会自动生成字段映射。'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 模式切换 */}
          <Tabs value={mode} onValueChange={(v) => setMode(v as 'file' | 'database')}>
            <TabsList>
              <TabsTrigger value="file">{t('dataSources.file') || '文件'}</TabsTrigger>
              <TabsTrigger value="database">{t('dataSources.database') || '数据库'}</TabsTrigger>
            </TabsList>
          </Tabs>

          {/* 选择数据对象 */}
          {mode === 'file' ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="border rounded-lg p-3">
                <div className="mb-2 text-sm font-medium">文件列表</div>
                <ScrollArea className="h-64 pr-2">
                  <div className="space-y-2">
                    {files.map((f) => (
                      <label
                        key={f.id}
                        className={cn(
                          'flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer',
                          selectedFileId === f.id ? 'border-primary bg-primary/5' : 'border-muted'
                        )}
                      >
                        <input
                          type="radio"
                          className="h-4 w-4"
                          checked={selectedFileId === f.id}
                          onChange={() => {
                            setSelectedFileId(f.id);
                            setSelectedColumns(new Set());
                          }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{f.original_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {f.row_count ?? '--'} 行 · {f.column_count ?? '--'} 列
                          </div>
                        </div>
                        {f.status && (
                          <Badge variant="secondary" className="shrink-0">
                            {f.status}
                          </Badge>
                        )}
                      </label>
                    ))}
                    {files.length === 0 && <div className="text-sm text-muted-foreground">暂无文件，请先上传</div>}
                  </div>
                </ScrollArea>
              </div>

              <div className="border rounded-lg p-3">
                <div className="mb-2 text-sm font-medium">列信息</div>
                {selectedFile ? (
                  <ScrollArea className="h-64 pr-2">
                    <div className="space-y-2">
                      {fileColumns.map((col) => (
                        <label
                          key={col.name}
                          className="flex items-center gap-2 text-sm cursor-pointer"
                          htmlFor={`file-col-${col.name}`}
                        >
                          <Checkbox
                            id={`file-col-${col.name}`}
                            checked={selectedColumns.has(col.name || '')}
                            onChange={() => toggleColumn(col.name || '')}
                          />
                          <span className="font-medium">{col.name}</span>
                          <span className="text-muted-foreground text-xs">{col.dtype}</span>
                        </label>
                      ))}
                      {fileColumns.length === 0 && <div className="text-sm text-muted-foreground">暂无列信息</div>}
                    </div>
                  </ScrollArea>
                ) : (
                  <div className="text-sm text-muted-foreground">请选择文件以查看列</div>
                )}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="border rounded-lg p-3 space-y-3">
                <div className="text-sm font-medium">选择连接 & 表</div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">连接</Label>
                  <ScrollArea className="h-24 pr-2">
                    <div className="space-y-2">
                      {connections.map((conn) => (
                        <label
                          key={conn.id}
                          className={cn(
                            'flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer',
                            selectedConnectionId === conn.id ? 'border-primary bg-primary/5' : 'border-muted'
                          )}
                        >
                          <input
                            type="radio"
                            className="h-4 w-4"
                            checked={selectedConnectionId === conn.id}
                            onChange={() => {
                              setSelectedConnectionId(conn.id);
                              setSelectedTable(null);
                              setSelectedColumns(new Set());
                            }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{conn.name}</div>
                            <div className="text-xs text-muted-foreground">{conn.db_type}</div>
                          </div>
                        </label>
                      ))}
                      {connections.length === 0 && <div className="text-sm text-muted-foreground">暂无连接</div>}
                    </div>
                  </ScrollArea>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground">表 / 视图</Label>
                  <ScrollArea className="h-32 pr-2">
                    <div className="space-y-2">
                      {tables.map((t) => (
                        <label
                          key={`${t.schema_name || 'public'}.${t.table_name}`}
                          className={cn(
                            'flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer',
                            selectedTable?.name === t.table_name && selectedTable?.schema === t.schema_name
                              ? 'border-primary bg-primary/5'
                              : 'border-muted'
                          )}
                          htmlFor={`table-${t.schema_name || 'public'}-${t.table_name}`}
                        >
                          <input
                            id={`table-${t.schema_name || 'public'}-${t.table_name}`}
                            type="radio"
                            className="h-4 w-4"
                            checked={selectedTable?.name === t.table_name && selectedTable?.schema === t.schema_name}
                            onChange={() => {
                              setSelectedTable({ schema: t.schema_name, name: t.table_name });
                              setSelectedColumns(new Set());
                            }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{t.table_name}</div>
                            <div className="text-xs text-muted-foreground">{t.schema_name || 'public'}</div>
                          </div>
                          <Badge variant="secondary" className="shrink-0">
                            {t.table_type}
                          </Badge>
                        </label>
                      ))}
                      {tables.length === 0 && <div className="text-sm text-muted-foreground">请选择连接后查看表</div>}
                    </div>
                  </ScrollArea>
                </div>
              </div>

              <div className="border rounded-lg p-3">
                <div className="mb-2 text-sm font-medium">列信息</div>
                {selectedTable ? (
                  <ScrollArea className="h-64 pr-2">
                    <div className="space-y-2">
                      {tableColumns.map((col) => (
                        <label
                          key={col.name}
                          className="flex items-center gap-2 text-sm cursor-pointer"
                          htmlFor={`db-col-${col.name}`}
                        >
                          <Checkbox
                            id={`db-col-${col.name}`}
                            checked={selectedColumns.has(col.name || '')}
                            onChange={() => toggleColumn(col.name || '')}
                          />
                          <span className="font-medium">{col.name}</span>
                          <span className="text-muted-foreground text-xs">{col.data_type}</span>
                          {col.primary_key && (
                            <Badge variant="outline" className="text-xs">
                              PK
                            </Badge>
                          )}
                        </label>
                      ))}
                      {tableColumns.length === 0 && <div className="text-sm text-muted-foreground">暂无列信息</div>}
                    </div>
                  </ScrollArea>
                ) : (
                  <div className="text-sm text-muted-foreground">请选择表以查看列</div>
                )}
              </div>
            </div>
          )}

          {/* 选中列预览 */}
          <div className="border rounded-lg p-3">
            <div className="mb-2 text-sm font-medium">已选列</div>
            {selectedColumns.size === 0 ? (
              <div className="text-sm text-muted-foreground">尚未选择列</div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {[...selectedColumns].map((col) => (
                  <Badge key={col} variant="secondary">
                    {col}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <div className="flex w-full items-center justify-between text-sm text-muted-foreground">
            <span>当前为预览向导，提交创建数据源的能力稍后打通。</span>
            <div className="space-x-2">
              <Button variant="outline" onClick={handleClose}>
                取消
              </Button>
              <Button disabled className="cursor-not-allowed" title="即将支持提交创建数据源">
                创建数据源（即将）
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
