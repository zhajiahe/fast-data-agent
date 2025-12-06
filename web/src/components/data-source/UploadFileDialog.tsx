import { FileSpreadsheet, Upload, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DataSourceType, useCreateDataSource, useUploadFile } from '@/api';
import { LoadingSpinner } from '@/components/common';
import { Button } from '@/components/ui/button';
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
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';

interface UploadFileDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const acceptedExtensions = ['.csv', '.xls', '.xlsx', '.json', '.parquet'];

/**
 * 上传文件对话框
 */
export const UploadFileDialog = ({ open, onOpenChange }: UploadFileDialogProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragOver, setIsDragOver] = useState(false);

  // 使用生成的 API hooks
  const uploadFileMutation = useUploadFile();
  const createDataSourceMutation = useCreateDataSource();

  const isUploading = uploadFileMutation.isPending || createDataSourceMutation.isPending;

  const isValidFile = (selectedFile: File): boolean => {
    const ext = `.${selectedFile.name.split('.').pop()?.toLowerCase()}`;
    if (!acceptedExtensions.includes(ext)) {
      toast({
        title: t('files.invalidType'),
        description: t('files.acceptedTypes', { types: acceptedExtensions.join(', ') }),
        variant: 'destructive',
      });
      return false;
    }
    return true;
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && isValidFile(droppedFile)) {
      setFile(droppedFile);
      if (!name) {
        setName(droppedFile.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && isValidFile(selectedFile)) {
      setFile(selectedFile);
      if (!name) {
        setName(selectedFile.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleUpload = async () => {
    if (!file || !name.trim()) return;

    setUploadProgress(0);

    try {
      // 1. 上传文件
      const uploadResult = await uploadFileMutation.mutateAsync({ file });
      setUploadProgress(50);

      const fileId = uploadResult.data.data?.id;
      if (!fileId) {
        throw new Error('上传文件失败：未获取到文件 ID');
      }

      // 2. 创建文件类型数据源
      await createDataSourceMutation.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        source_type: DataSourceType.file,
        file_id: fileId,
      });

      setUploadProgress(100);

      toast({
        title: t('common.success'),
        description: t('files.uploadSuccess'),
      });

      handleClose();
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '上传失败';
      toast({
        title: t('common.error'),
        description: errorMessage,
        variant: 'destructive',
      });
    }
  };

  const handleClose = () => {
    setFile(null);
    setName('');
    setDescription('');
    setUploadProgress(0);
    onOpenChange(false);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            {t('dataSources.uploadFile')}
          </DialogTitle>
          <DialogDescription>{t('dataSources.uploadFileDesc')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 拖拽上传区域 */}
          {!file ? (
            // biome-ignore lint/a11y/useSemanticElements: 拖放区域需要 div 以支持拖放事件
            <div
              role="button"
              tabIndex={0}
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
                isDragOver
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/25 hover:border-muted-foreground/50'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  document.getElementById('file-input')?.click();
                }
              }}
              onClick={() => document.getElementById('file-input')?.click()}
            >
              <FileSpreadsheet className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground mb-2">{t('files.dragOrClick')}</p>
              <p className="text-xs text-muted-foreground mb-4">
                {t('files.acceptedTypes', { types: acceptedExtensions.join(', ') })}
              </p>
              <input
                id="file-input"
                type="file"
                className="hidden"
                accept={acceptedExtensions.join(',')}
                onChange={handleFileChange}
              />
              <Button type="button" variant="outline" size="sm">
                {t('files.selectFile')}
              </Button>
            </div>
          ) : (
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileSpreadsheet className="h-8 w-8 text-green-500" />
                  <div>
                    <p className="font-medium text-sm">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setFile(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              {isUploading && (
                <div className="mt-3">
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 text-center">
                    {uploadProgress < 50 ? '上传中...' : '创建数据源...'}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 名称 */}
          <div className="space-y-2">
            <Label htmlFor="name">{t('dataSources.name')}</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="数据源名称" />
          </div>

          {/* 描述 */}
          <div className="space-y-2">
            <Label htmlFor="description">{t('dataSources.description')}</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="可选的描述信息"
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isUploading}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleUpload} disabled={!file || !name.trim() || isUploading}>
            {isUploading ? (
              <>
                <LoadingSpinner size="sm" className="mr-2 text-current" />
                {t('files.uploading')}
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                {t('files.upload')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
