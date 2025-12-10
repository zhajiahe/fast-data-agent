import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  RawDataType,
  useCreateDataSource,
  useCreateRawData,
  useDbConnections,
  useDbTableSchema,
  useDbTables,
  useFiles,
  useRawDataList,
} from '@/api';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
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
  const { toast } = useToast();
  const createDataSource = useCreateDataSource();
  const createRawData = useCreateRawData();
  const [selectedFileIds, setSelectedFileIds] = useState<Set<number>>(new Set());
  const [focusedFileId, setFocusedFileId] = useState<number | null>(null);
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(null);
  const [selectedTables, setSelectedTables] = useState<Array<{ schema?: string | null; name: string }>>([]);
  const [focusedTable, setFocusedTable] = useState<{ schema?: string | null; name: string } | null>(null);
  const [fileSelectedColumns, setFileSelectedColumns] = useState<Record<number, Set<string>>>({});
  const [tableSelectedColumns, setTableSelectedColumns] = useState<Record<string, Set<string>>>({});
  const [tableColumnsCache, setTableColumnsCache] = useState<Record<string, any[]>>({});
  const [dataSourceName, setDataSourceName] = useState<string>('');

  // 文件数据
  const { data: filesResp } = useFiles();
  const files = filesResp?.data.data?.items || [];
  const selectedFiles = files.filter((f) => selectedFileIds.has(f.id));
  const selectedFile = files.find((f) => f.id === focusedFileId) || selectedFiles[0];
  const fileColumns = (selectedFile?.columns_info as { name?: string; dtype?: string }[] | undefined) || [];

  const selectedColsForFocusedFile = useMemo(() => {
    if (!selectedFile) return new Set<string>();
    return fileSelectedColumns[selectedFile.id] || new Set<string>();
  }, [selectedFile, fileSelectedColumns]);

  const _selectedFileColumnsPreview = useMemo(() => {
    const merged = new Set<string>();
    Object.values(fileSelectedColumns).forEach((s) => {
      s.forEach((name) => {
        merged.add(name);
      });
    });
    return Array.from(merged);
  }, [fileSelectedColumns]);

  // 数据库连接与表
  const { data: connResp } = useDbConnections();
  const connections = connResp?.data.data?.items || [];
  const { data: tablesResp } = useDbTables(selectedConnectionId || undefined);
  const tables = tablesResp?.data.data?.tables || [];

  // RawData 列表（用于匹配 raw_data_id）
  const { data: rawDataResp } = useRawDataList();
  const rawDataList = rawDataResp?.data.data?.items || [];

  // 列信息（数据库表）
  const { data: schemaResp } = useDbTableSchema(
    selectedConnectionId || undefined,
    focusedTable
      ? {
          schema_name: focusedTable.schema || undefined,
          table_name: focusedTable.name,
        }
      : undefined
  );
  const tableColumns = schemaResp?.data.data?.columns || [];

  const tableKey = useCallback(
    (table: { schema?: string | null; name: string }) => `${table.schema || 'public'}.${table.name}`,
    []
  );

  const focusedTableKey = focusedTable ? tableKey(focusedTable) : null;

  const selectedColsForFocused = useMemo(() => {
    if (!focusedTableKey) return new Set<string>();
    return tableSelectedColumns[focusedTableKey] || new Set<string>();
  }, [focusedTableKey, tableSelectedColumns]);

  // 缓存当前聚焦表的列信息，便于后续提交使用
  useEffect(() => {
    if (!focusedTableKey) return;
    setTableColumnsCache((prev) => {
      if (tableColumns.length === 0) return prev;
      return { ...prev, [focusedTableKey]: tableColumns };
    });
  }, [focusedTableKey, tableColumns]);

  const toggleFileColumn = (fileId: number, name: string) => {
    setFileSelectedColumns((prev) => {
      const current = prev[fileId] ? new Set(prev[fileId]) : new Set<string>();
      if (current.has(name)) current.delete(name);
      else current.add(name);
      return { ...prev, [fileId]: current };
    });
  };

  const toggleTableColumn = (name: string) => {
    if (!focusedTableKey) return;
    setTableSelectedColumns((prev) => {
      const current = prev[focusedTableKey] ? new Set(prev[focusedTableKey]) : new Set<string>();
      if (current.has(name)) current.delete(name);
      else current.add(name);
      return { ...prev, [focusedTableKey]: current };
    });
  };

  const handleClose = () => {
    setSelectedFileIds(new Set());
    setFocusedFileId(null);
    setSelectedConnectionId(null);
    setSelectedTables([]);
    setFocusedTable(null);
    setFileSelectedColumns({});
    setTableSelectedColumns({});
    setTableColumnsCache({});
    setDataSourceName('');
    onOpenChange(false);
  };

  const updateDefaultName = (name: string | undefined) => {
    if (name && !dataSourceName) {
      setDataSourceName(name);
    }
  };

  const findRawDataIdForFile = (fileId: number): number | null => {
    const rd = rawDataList.find((r: any) => r.file_id === fileId);
    return rd?.id || null;
  };

  const findRawDataId = (table?: { schema?: string | null; name: string } | null): number | null => {
    if (selectedConnectionId && table) {
      const rd = rawDataList.find(
        (r: any) =>
          r.connection_id === selectedConnectionId &&
          r.table_name === table.name &&
          (r.schema_name || null) === (table.schema || null)
      );
      return rd?.id || null;
    }
    return null;
  };

  const toggleTable = (table: { schema?: string | null; name: string }) => {
    const key = tableKey(table);
    const exists = selectedTables.some((t) => tableKey(t) === key);
    if (exists) {
      const nextTables = selectedTables.filter((t) => tableKey(t) !== key);
      const { [key]: _, ...rest } = tableSelectedColumns;
      const { [key]: __, ...restColumnsCache } = tableColumnsCache;
      setSelectedTables(nextTables);
      setTableSelectedColumns(rest);
      setTableColumnsCache(restColumnsCache);
      if (focusedTableKey === key) {
        setFocusedTable(nextTables[0] ?? null);
      }
    } else {
      setSelectedTables((prev) => [...prev, table]);
      setFocusedTable(table);
      setTableSelectedColumns((prev) => ({ ...prev, [key]: prev[key] || new Set<string>() }));
    }
    // 重置数据源名称以最近选择的表为默认（仅当未填写）
    updateDefaultName(table.name);
  };

  const selectedTableBadges = useMemo(
    () =>
      selectedTables.map((t) => ({
        key: tableKey(t),
        label: `${t.schema || 'public'}.${t.name}`,
        count: tableSelectedColumns[tableKey(t)]?.size || 0,
      })),
    [selectedTables, tableSelectedColumns, tableKey]
  );

  const _unionTargetFieldsFromTables = () => {
    const fieldMap: Record<string, { data_type: string; description?: string }> = {};
    for (const t of selectedTables) {
      const key = tableKey(t);
      const cols = tableColumnsCache[key];
      const selectedSet = tableSelectedColumns[key];
      if (!cols || !selectedSet || selectedSet.size === 0) continue;
      cols.forEach((c: any) => {
        if (selectedSet.has(c.name)) {
          fieldMap[c.name] = {
            data_type: c.data_type || 'string',
            description: c.comment || undefined,
          };
        }
      });
    }
    return Object.entries(fieldMap).map(([name, meta]) => ({
      name,
      data_type: meta.data_type,
      description: meta.description,
    }));
  };

  const handleSubmit = async () => {
    if (!dataSourceName.trim()) {
      toast({ title: '请填写数据源名称', variant: 'destructive' });
      return;
    }
    // 文件映射
    const fileRawMappings: Array<{
      raw_data_id: number;
      mappings: Record<string, string>;
      priority: number;
      is_enabled: boolean;
    }> = [];
    const targetFieldMap: Record<string, { data_type: string; description?: string }> = {};
    selectedFiles.forEach((f, idx) => {
      const cols = (f.columns_info as any[]) || [];
      const selectedSet = fileSelectedColumns[f.id] || new Set<string>();
      if (selectedSet.size === 0) return;
      const rawId = findRawDataIdForFile(f.id);
      if (!rawId) return;
      const mappings: Record<string, string> = {};
      cols.forEach((c) => {
        if (selectedSet.has(c.name)) {
          mappings[c.name] = c.name;
          if (!targetFieldMap[c.name]) {
            targetFieldMap[c.name] = {
              data_type: c.dtype || 'string',
              description: c.comment || undefined,
            };
          }
        }
      });
      if (Object.keys(mappings).length > 0) {
        fileRawMappings.push({ raw_data_id: rawId, mappings, priority: idx, is_enabled: true });
      }
    });

    // 数据库表映射
    const missingColumnsTables: string[] = [];
    const emptySelectionTables: string[] = [];
    const missingRawDataTables: string[] = [];
    const rawDataMap: Record<string, number> = {};
    const tableRawMappings: Array<{
      raw_data_id: number;
      mappings: Record<string, string>;
      priority: number;
      is_enabled: boolean;
    }> = [];

    selectedTables.forEach((table) => {
      const key = tableKey(table);
      const existingId = findRawDataId(table);
      if (existingId) {
        rawDataMap[key] = existingId;
      } else {
        missingRawDataTables.push(key);
      }
    });

    if (missingRawDataTables.length > 0 && selectedConnectionId) {
      try {
        for (const tableKeyStr of missingRawDataTables) {
          const table = selectedTables.find((t) => tableKey(t) === tableKeyStr);
          if (!table) continue;
          const created = await createRawData.mutateAsync({
            name: `${table.schema || 'public'}.${table.name}`,
            description: `自动创建自表 ${table.schema || 'public'}.${table.name}`,
            raw_type: RawDataType.database_table,
            database_table_config: {
              connection_id: selectedConnectionId,
              schema_name: table.schema || undefined,
              table_name: table.name,
            },
          } as any);
          const newId = created.data.data?.id;
          if (newId) rawDataMap[tableKeyStr] = newId;
        }
        missingRawDataTables.length = 0;
      } catch (error) {
        const message = error instanceof Error ? error.message : '自动创建 RawData 失败';
        toast({ title: '创建 RawData 失败', description: message, variant: 'destructive' });
        return;
      }
    }

    selectedTables.forEach((table, idx) => {
      const key = tableKey(table);
      const cols = tableColumnsCache[key];
      const selectedSet = tableSelectedColumns[key];
      if (!cols) {
        missingColumnsTables.push(key);
        return;
      }
      if (!selectedSet || selectedSet.size === 0) {
        emptySelectionTables.push(key);
        return;
      }
      const rawDataId = rawDataMap[key] ?? findRawDataId(table);
      if (!rawDataId) {
        missingRawDataTables.push(key);
        return;
      }
      const mappings: Record<string, string> = {};
      cols.forEach((c: any) => {
        if (selectedSet.has(c.name)) {
          mappings[c.name] = c.name;
          if (!targetFieldMap[c.name]) {
            targetFieldMap[c.name] = {
              data_type: c.data_type || 'string',
              description: c.comment || undefined,
            };
          }
        }
      });
      if (Object.keys(mappings).length > 0) {
        tableRawMappings.push({
          raw_data_id: rawDataId,
          mappings,
          priority: idx,
          is_enabled: true,
        });
      }
    });

    const rawMappings = [...fileRawMappings, ...tableRawMappings];
    const target_fields = Object.entries(targetFieldMap).map(([name, meta]) => ({
      name,
      data_type: meta.data_type,
      description: meta.description,
    }));

    if (rawMappings.length === 0 || target_fields.length === 0) {
      toast({ title: '请选择至少一个文件或表的列', variant: 'destructive' });
      return;
    }

    await createDataSource.mutateAsync({
      name: dataSourceName.trim(),
      target_fields,
      raw_mappings: rawMappings,
    } as any);
    toast({ title: '创建数据源成功' });
    handleClose();
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
          {/* 数据源名称 */}
          <div className="space-y-2">
            <Label htmlFor="ds-name">数据源名称</Label>
            <Input
              id="ds-name"
              value={dataSourceName}
              onChange={(e) => setDataSourceName(e.target.value)}
              placeholder="例如：销售数据源"
            />
          </div>

          {/* 选择数据对象（文件 + 数据库表，可混合） */}
          <div className="grid grid-cols-2 gap-4">
            <div className="border rounded-lg p-3">
              <div className="mb-2 text-sm font-medium">文件列表（可多选）</div>
              <ScrollArea className="h-64 pr-2">
                <div className="space-y-2">
                  {files.map((f) => {
                    const checked = selectedFileIds.has(f.id);
                    const inputId = `file-item-${f.id}`;
                    return (
                      <button
                        type="button"
                        key={f.id}
                        className={cn(
                          'flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer',
                          checked ? 'border-primary bg-primary/5' : 'border-muted'
                        )}
                        onClick={() => setFocusedFileId(f.id)}
                      >
                        <Checkbox
                          id={inputId}
                          checked={checked}
                          onChange={(e) => {
                            const v = e.target.checked;
                            setSelectedFileIds((prev) => {
                              const next = new Set(prev);
                              if (v) next.add(f.id);
                              else next.delete(f.id);
                              if (!next.has(focusedFileId || -1)) {
                                const first = Array.from(next)[0] ?? null;
                                setFocusedFileId(first);
                              }
                              return next;
                            });
                            updateDefaultName(f.original_name || '');
                          }}
                          className="pointer-events-auto"
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
                      </button>
                    );
                  })}
                  {files.length === 0 && <div className="text-sm text-muted-foreground">暂无文件，请先上传</div>}
                </div>
              </ScrollArea>
              <div className="mt-2 text-xs text-muted-foreground">
                已选 {selectedFileIds.size} 个文件，点击文件可切换右侧列预览
              </div>
            </div>

            <div className="border rounded-lg p-3">
              <div className="mb-2 text-sm font-medium">列信息（当前聚焦文件）</div>
              {selectedFile ? (
                <ScrollArea className="h-64 pr-2">
                  <div className="space-y-2">
                    {fileColumns.map((col) => {
                      const checked = selectedColsForFocusedFile.has(col.name || '');
                      return (
                        <label
                          key={col.name}
                          className="flex items-center gap-2 text-sm cursor-pointer"
                          htmlFor={`file-col-${col.name}`}
                        >
                          <Checkbox
                            id={`file-col-${col.name}`}
                            checked={checked}
                            onChange={() => selectedFile && toggleFileColumn(selectedFile.id, col.name || '')}
                            className="pointer-events-auto"
                          />
                          <span className="font-medium">{col.name}</span>
                          <span className="text-muted-foreground text-xs">{col.dtype || 'string'}</span>
                        </label>
                      );
                    })}
                    {fileColumns.length === 0 && <div className="text-sm text-muted-foreground">暂无列信息</div>}
                  </div>
                </ScrollArea>
              ) : (
                <div className="text-sm text-muted-foreground">请选择文件以查看列</div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="border rounded-lg p-3 space-y-3">
              <div className="text-sm font-medium">选择数据库</div>
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
                            setSelectedTables([]);
                            setFocusedTable(null);
                            setTableSelectedColumns({});
                            setTableColumnsCache({});
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
                    {tables.map((t) => {
                      const tableRef = { schema: t.schema_name, name: t.table_name };
                      const key = tableKey(tableRef);
                      const checked = selectedTables.some((st) => tableKey(st) === key);
                      return (
                        <button
                          type="button"
                          key={key}
                          className={cn(
                            'flex w-full items-center gap-2 rounded-md border px-3 py-2 text-left',
                            checked ? 'border-primary bg-primary/5' : 'border-muted'
                          )}
                          onClick={() => {
                            toggleTable(tableRef);
                            setFocusedTable(tableRef);
                            updateDefaultName(t.table_name);
                          }}
                        >
                          <Checkbox id={`table-${key}`} checked={checked} readOnly className="pointer-events-none" />
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{t.table_name}</div>
                            <div className="text-xs text-muted-foreground">{t.schema_name || 'public'}</div>
                          </div>
                          <Badge variant="secondary" className="shrink-0">
                            {t.table_type}
                          </Badge>
                        </button>
                      );
                    })}
                    {tables.length === 0 && <div className="text-sm text-muted-foreground">请选择连接后查看表</div>}
                  </div>
                </ScrollArea>
              </div>
            </div>

            <div className="border rounded-lg p-3">
              <div className="mb-2 text-sm font-medium">
                列信息 {focusedTable ? `· ${focusedTable.schema || 'public'}.${focusedTable.name}` : ''}
              </div>
              {focusedTable ? (
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
                          checked={selectedColsForFocused.has(col.name || '')}
                          onChange={() => toggleTableColumn(col.name || '')}
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
          {/* 选中列预览 */}
          <div className="border rounded-lg p-3 space-y-3">
            <div className="text-sm font-medium">已选列</div>

            {/* 按文件分组展示 */}
            {selectedFiles.length > 0 ? (
              <div className="space-y-2">
                {selectedFiles.map((f) => {
                  const cols = Array.from(fileSelectedColumns[f.id] || new Set<string>());
                  return (
                    <div key={`file-preview-${f.id}`} className="flex items-start gap-2">
                      <Badge variant="outline" className="shrink-0">
                        {f.original_name || `文件 #${f.id}`}
                      </Badge>
                      {cols.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {cols.map((c) => (
                            <Badge key={`file-${f.id}-${c}`} variant="secondary">
                              {c}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">未选列</span>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">未选择文件列</div>
            )}

            {/* 按表分组展示 */}
            {selectedTables.length > 0 ? (
              <div className="space-y-2">
                {selectedTableBadges.map((item) => (
                  <div key={item.key} className="flex items-start gap-2">
                    <Badge variant="outline" className="shrink-0">
                      {item.label}
                    </Badge>
                    <div className="flex flex-wrap gap-1">
                      {[...(tableSelectedColumns[item.key] || new Set<string>())].map((col) => (
                        <Badge key={`${item.key}-${col}`} variant="secondary">
                          {col}
                        </Badge>
                      ))}
                      {(!tableSelectedColumns[item.key] || tableSelectedColumns[item.key]?.size === 0) && (
                        <span className="text-xs text-muted-foreground">未选列</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">未选择表列</div>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleClose}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={createDataSource.isPending}>
            {createDataSource.isPending ? '创建中...' : '创建数据源'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
