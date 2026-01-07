import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, File, FileCode, FileImage, FileText, FolderOpen, Loader2, RefreshCw, Upload } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { listSessionFilesApiV1SessionsSessionIdFilesGet } from '@/api';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { storage } from '@/utils/storage';

interface SessionFilesPanelProps {
  sessionId: string;
}

interface SessionFile {
  name: string;
  size: number;
  modified: number;
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const getFileIcon = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'csv':
    case 'xlsx':
    case 'xls':
    case 'parquet':
      return <FileText className="h-4 w-4 text-green-500" />;
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'gif':
    case 'svg':
      return <FileImage className="h-4 w-4 text-purple-500" />;
    case 'py':
    case 'js':
    case 'ts':
    case 'json':
    case 'html':
      return <FileCode className="h-4 w-4 text-blue-500" />;
    default:
      return <File className="h-4 w-4 text-muted-foreground" />;
  }
};

/**
 * 会话文件面板（内联版本）
 */
export const SessionFilesPanel = ({ sessionId }: SessionFilesPanelProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [isDragging, setIsDragging] = useState(false);

  const {
    data: filesResponse,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['sessionFiles', sessionId],
    queryFn: () => listSessionFilesApiV1SessionsSessionIdFilesGet(sessionId),
    enabled: !!sessionId,
  });

  const files = (filesResponse?.data?.data as { files?: SessionFile[] })?.files || [];

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const token = storage.getToken();
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`/api/v1/sessions/${sessionId}/files/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
      return response.json();
    },
    onSuccess: () => {
      toast({ title: t('sessionFiles.uploadSuccess') });
      queryClient.invalidateQueries({ queryKey: ['sessionFiles', sessionId] });
    },
    onError: (error) => {
      toast({ title: t('sessionFiles.uploadFailed'), description: String(error), variant: 'destructive' });
    },
  });

  const handleDownload = useCallback(
    async (filename: string) => {
      const token = storage.getToken();
      const response = await fetch(`/api/v1/sessions/${sessionId}/files/${filename}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        toast({ title: t('sessionFiles.downloadFailed'), variant: 'destructive' });
        return;
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename.split('/').pop() || filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    },
    [sessionId, toast, t]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) uploadMutation.mutate(droppedFile);
    },
    [uploadMutation]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) uploadMutation.mutate(selectedFile);
      e.target.value = '';
    },
    [uploadMutation]
  );

  return (
    <div className="h-full flex flex-col">
      {/* 标题 */}
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FolderOpen className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">{t('sessionFiles.title')}</span>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* 内容区域 */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {/* 上传区域 - 拖放区域需要 div 以支持拖放事件 */}
          {/* biome-ignore lint/a11y/useSemanticElements: drag-drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer ${
              isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-muted-foreground/50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('session-file-input')?.click()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') document.getElementById('session-file-input')?.click();
            }}
            role="button"
            tabIndex={0}
          >
            {uploadMutation.isPending ? (
              <Loader2 className="h-6 w-6 mx-auto text-primary animate-spin" />
            ) : (
              <Upload className="h-6 w-6 mx-auto text-muted-foreground" />
            )}
            <p className="mt-1 text-xs text-muted-foreground">
              {uploadMutation.isPending ? t('sessionFiles.uploading') : t('sessionFiles.dragOrClick')}
            </p>
            <input id="session-file-input" type="file" className="hidden" onChange={handleFileSelect} />
          </div>

          {/* 文件列表 */}
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">
              <File className="h-8 w-8 mx-auto mb-1 opacity-30" />
              <p className="text-xs">{t('sessionFiles.noFiles')}</p>
            </div>
          ) : (
            <div className="space-y-1">
              {files.map((file) => (
                <div
                  key={file.name}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 group"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {getFileIcon(file.name)}
                    <div className="min-w-0">
                      <p className="text-xs font-medium truncate" title={file.name}>
                        {file.name}
                      </p>
                      <p className="text-[10px] text-muted-foreground">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleDownload(file.name)}
                  >
                    <Download className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};
