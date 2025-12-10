import { FileSpreadsheet, Upload, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { type DataSourceCreate, useCreateDataSource, useUploadFile } from '@/api';
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
 * 上传文件对话框（支持多文件批量上传）
 */
export const UploadFileDialog = ({ open, onOpenChange }: UploadFileDialogProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [files, setFiles] = useState<File[]>([]);
  const [groupName, setGroupName] = useState('');
  const [description, setDescription] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [isDragOver, setIsDragOver] = useState(false);

  // 使用生成的 API hooks
  const uploadFileMutation = useUploadFile();
  const createDataSourceMutation = useCreateDataSource();

  const isUploading = uploadFileMutation.isPending || createDataSourceMutation.isPending;

  const isValidFile = (selectedFile: File): boolean => {
    const ext = `.${selectedFile.name.split('.').pop()?.toLowerCase()}`;
    return acceptedExtensions.includes(ext);
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
    const droppedFiles = Array.from(e.dataTransfer.files).filter(isValidFile);
    if (droppedFiles.length > 0) {
      setFiles((prev) => [...prev, ...droppedFiles]);
      if (!groupName && droppedFiles.length === 1) {
        setGroupName(droppedFiles[0].name.replace(/\.[^/.]+$/, ''));
      } else if (!groupName && droppedFiles.length > 1) {
        setGroupName(t('dataSources.newGroup'));
      }
    }
    if (droppedFiles.length < e.dataTransfer.files.length) {
      toast({
        title: t('files.invalidType'),
        description: t('files.acceptedTypes', { types: acceptedExtensions.join(', ') }),
        variant: 'destructive',
      });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []).filter(isValidFile);
    if (selectedFiles.length > 0) {
      setFiles((prev) => [...prev, ...selectedFiles]);
      if (!groupName && selectedFiles.length === 1) {
        setGroupName(selectedFiles[0].name.replace(/\.[^/.]+$/, ''));
      } else if (!groupName && selectedFiles.length > 1) {
        setGroupName(t('dataSources.newGroup'));
      }
    }
    // Reset input
    e.target.value = '';
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0 || !groupName.trim()) return;

    setUploadProgress(0);
    setCurrentFileIndex(0);

    const totalFiles = files.length;
    const progressPerFile = 100 / totalFiles;

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setCurrentFileIndex(i);

        // 1. 上传文件
        const uploadResult = await uploadFileMutation.mutateAsync({ file });
        setUploadProgress((i + 0.5) * progressPerFile);

        const fileId = uploadResult.data.data?.id;
        if (!fileId) {
          throw new Error(`上传文件 ${file.name} 失败：未获取到文件 ID`);
        }

        // 2. 创建文件类型数据源（使用文件名作为数据源名称，group_name 作为分组）
        const dataSourceName = files.length === 1 ? groupName.trim() : file.name.replace(/\.[^/.]+$/, '');
        await createDataSourceMutation.mutateAsync({
          name: dataSourceName,
          description: description.trim() || undefined,
          file_id: fileId,
          group_name: files.length > 1 ? groupName.trim() : undefined,
        } as unknown as DataSourceCreate);

        setUploadProgress((i + 1) * progressPerFile);
      }

      toast({
        title: t('common.success'),
        description:
          files.length === 1 ? t('files.uploadSuccess') : t('files.uploadSuccessMultiple', { count: files.length }),
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
    setFiles([]);
    setGroupName('');
    setDescription('');
    setUploadProgress(0);
    setCurrentFileIndex(0);
    onOpenChange(false);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            {t('dataSources.uploadFile')}
          </DialogTitle>
          <DialogDescription>{t('dataSources.uploadFileDescMultiple')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 拖拽上传区域 */}
          {/* biome-ignore lint/a11y/useSemanticElements: 拖放区域需要 div 以支持拖放事件 */}
          <div
            role="button"
            tabIndex={0}
            className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
              isDragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-muted-foreground/50'
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
            <FileSpreadsheet className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground mb-1">{t('files.dragOrClickMultiple')}</p>
            <p className="text-xs text-muted-foreground mb-3">
              {t('files.acceptedTypes', { types: acceptedExtensions.join(', ') })}
            </p>
            <input
              id="file-input"
              type="file"
              className="hidden"
              accept={acceptedExtensions.join(',')}
              multiple
              onChange={handleFileChange}
            />
            <Button type="button" variant="outline" size="sm">
              {t('files.selectFiles')}
            </Button>
          </div>

          {/* 已选择的文件列表 */}
          {files.length > 0 && (
            <div className="border rounded-lg divide-y max-h-[180px] overflow-y-auto">
              {files.map((file, index) => (
                <div key={`${file.name}-${index}`} className="flex items-center justify-between p-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileSpreadsheet className="h-6 w-6 text-green-500 shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{file.name}</p>
                      <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => removeFile(index)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* 上传进度 */}
          {isUploading && (
            <div className="space-y-2">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground text-center">
                {t('files.uploadingFile', { current: currentFileIndex + 1, total: files.length })}
              </p>
            </div>
          )}

          {/* 组名/数据源名称 */}
          <div className="space-y-2">
            <Label htmlFor="groupName">{files.length > 1 ? t('dataSources.groupName') : t('dataSources.name')}</Label>
            <Input
              id="groupName"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder={files.length > 1 ? t('dataSources.groupNamePlaceholder') : t('dataSources.namePlaceholder')}
            />
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
          <Button onClick={handleUpload} disabled={files.length === 0 || !groupName.trim() || isUploading}>
            {isUploading ? (
              <>
                <LoadingSpinner size="sm" className="mr-2 text-current" />
                {t('files.uploading')}
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                {files.length > 1 ? t('files.uploadCount', { count: files.length }) : t('files.upload')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
