import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FolderOpen,
  Upload,
  Download,
  FileText,
  FileImage,
  FileCode,
  File,
  RefreshCw,
  X,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { useToast } from '@/hooks/use-toast';
import { storage } from '@/utils/storage';
import { listSessionFilesApiV1SessionsSessionIdFilesGet } from '@/api/fastDataAgent';

interface SessionFilesPanelProps {
  sessionId: number;
}

interface SessionFile {
  name: string;
  size: number;
  modified: number;
}

// 文件大小格式化
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

// 获取文件图标
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
 * 会话文件面板 - 显示、上传、下载会话目录中的文件
 */
export const SessionFilesPanel = ({ sessionId }: SessionFilesPanelProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [isOpen, setIsOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // 获取文件列表
  const {
    data: filesResponse,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['sessionFiles', sessionId],
    queryFn: () => listSessionFilesApiV1SessionsSessionIdFilesGet(sessionId),
    enabled: isOpen && !!sessionId,
  });

  const files: SessionFile[] = filesResponse?.data?.data?.files || [];

  // 上传文件
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const token = storage.getToken();
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`/api/v1/sessions/${sessionId}/files/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      return response.json();
    },
    onSuccess: () => {
      toast({
        title: t('sessionFiles.uploadSuccess'),
        description: t('sessionFiles.uploadSuccessDesc'),
      });
      queryClient.invalidateQueries({ queryKey: ['sessionFiles', sessionId] });
    },
    onError: (error) => {
      toast({
        title: t('sessionFiles.uploadFailed'),
        description: String(error),
        variant: 'destructive',
      });
    },
  });

  // 下载文件
  const handleDownload = useCallback(
    async (filename: string) => {
      const token = storage.getToken();
      const response = await fetch(`/api/v1/sessions/${sessionId}/files/${filename}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        toast({
          title: t('sessionFiles.downloadFailed'),
          variant: 'destructive',
        });
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

  // 拖拽上传
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
      if (droppedFile) {
        uploadMutation.mutate(droppedFile);
      }
    },
    [uploadMutation]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        uploadMutation.mutate(selectedFile);
      }
      e.target.value = ''; // Reset input
    },
    [uploadMutation]
  );

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" title={t('sessionFiles.title')}>
          <FolderOpen className="h-5 w-5" />
        </Button>
      </SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5" />
            {t('sessionFiles.title')}
          </SheetTitle>
          <SheetDescription>{t('sessionFiles.description')}</SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {/* 上传区域 */}
          <div
            className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
              isDragging
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-muted-foreground/50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('session-file-input')?.click()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                document.getElementById('session-file-input')?.click();
              }
            }}
            role="button"
            tabIndex={0}
          >
            {uploadMutation.isPending ? (
              <Loader2 className="h-8 w-8 mx-auto text-primary animate-spin" />
            ) : (
              <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
            )}
            <p className="mt-2 text-sm text-muted-foreground">
              {uploadMutation.isPending
                ? t('sessionFiles.uploading')
                : t('sessionFiles.dragOrClick')}
            </p>
            <input
              id="session-file-input"
              type="file"
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>

          {/* 文件列表 */}
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium">{t('sessionFiles.fileList')}</h4>
            <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <File className="h-12 w-12 mx-auto mb-2 opacity-30" />
              <p className="text-sm">{t('sessionFiles.noFiles')}</p>
            </div>
          ) : (
            <div className="space-y-1 max-h-[400px] overflow-y-auto">
              {files.map((file) => (
                <div
                  key={file.name}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 group"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {getFileIcon(file.name)}
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate" title={file.name}>
                        {file.name}
                      </p>
                      <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={() => handleDownload(file.name)}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};

