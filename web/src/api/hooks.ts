/**
 * API React Query Hooks
 * 封装生成的 API 函数为 React Query hooks
 */
import { useQuery, useMutation, useQueryClient, type UseQueryOptions, type UseMutationOptions } from '@tanstack/react-query';
import type { AxiosResponse } from 'axios';

// 导入 API 配置（初始化 axios 拦截器）
import './config';

// 导入生成的 API 函数
import {
  // Auth
  loginApiV1AuthLoginPost,
  registerApiV1AuthRegisterPost,
  getCurrentUserInfoApiV1AuthMeGet,
  // Data Sources
  getDataSourcesApiV1DataSourcesGet,
  createDataSourceApiV1DataSourcesPost,
  deleteDataSourceApiV1DataSourcesDataSourceIdDelete,
  testDataSourceConnectionApiV1DataSourcesDataSourceIdTestPost,
  syncDataSourceSchemaApiV1DataSourcesDataSourceIdSyncSchemaPost,
  // Files
  getFilesApiV1FilesGet,
  uploadFileApiV1FilesUploadPost,
  deleteFileApiV1FilesFileIdDelete,
  // Sessions
  getSessionsApiV1SessionsGet,
  createSessionApiV1SessionsPost,
  getSessionApiV1SessionsSessionIdGet,
  deleteSessionApiV1SessionsSessionIdDelete,
  archiveSessionApiV1SessionsSessionIdArchivePost,
  // Messages
  getMessagesApiV1SessionsSessionIdMessagesGet,
  clearMessagesApiV1SessionsSessionIdMessagesDelete,
  // Recommendations
  getRecommendationsApiV1SessionsSessionIdRecommendationsGet,
  generateRecommendationsApiV1SessionsSessionIdRecommendationsPost,
  updateRecommendationApiV1SessionsSessionIdRecommendationsRecommendationIdPut,
} from './fastDataAgent';

// 导入类型
import type {
  LoginRequest,
  UserCreate,
  DataSourceCreate,
  AnalysisSessionCreate,
  GetDataSourcesApiV1DataSourcesGetParams,
  GetSessionsApiV1SessionsGetParams,
  GetMessagesApiV1SessionsSessionIdMessagesGetParams,
  GetRecommendationsApiV1SessionsSessionIdRecommendationsGetParams,
  GenerateRecommendationsApiV1SessionsSessionIdRecommendationsPostBody,
  TaskRecommendationUpdate,
  BodyUploadFileApiV1FilesUploadPost,
} from './fastDataAgent';

// ==================== Auth Hooks ====================

export const useLogin = (options?: UseMutationOptions<AxiosResponse, Error, LoginRequest>) => {
  return useMutation({
    mutationFn: (data: LoginRequest) => loginApiV1AuthLoginPost(data),
    ...options,
  });
};

export const useRegister = (options?: UseMutationOptions<AxiosResponse, Error, UserCreate>) => {
  return useMutation({
    mutationFn: (data: UserCreate) => registerApiV1AuthRegisterPost(data),
    ...options,
  });
};

export const useCurrentUser = (options?: Omit<UseQueryOptions, 'queryKey' | 'queryFn'>) => {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: () => getCurrentUserInfoApiV1AuthMeGet(),
    ...options,
  });
};

// ==================== Data Source Hooks ====================

export const useDataSources = (
  params?: GetDataSourcesApiV1DataSourcesGetParams,
  options?: Omit<UseQueryOptions, 'queryKey' | 'queryFn'>
) => {
  return useQuery({
    queryKey: ['dataSources', params],
    queryFn: () => getDataSourcesApiV1DataSourcesGet(params),
    ...options,
  });
};

export const useCreateDataSource = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DataSourceCreate) => createDataSourceApiV1DataSourcesPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

export const useDeleteDataSource = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteDataSourceApiV1DataSourcesDataSourceIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

export const useTestDataSourceConnection = () => {
  return useMutation({
    mutationFn: (id: number) => testDataSourceConnectionApiV1DataSourcesDataSourceIdTestPost(id),
  });
};

export const useSyncDataSourceSchema = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => syncDataSourceSchemaApiV1DataSourcesDataSourceIdSyncSchemaPost(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

// ==================== File Hooks ====================

export const useFiles = (options?: Omit<UseQueryOptions, 'queryKey' | 'queryFn'>) => {
  return useQuery({
    queryKey: ['files'],
    queryFn: () => getFilesApiV1FilesGet(),
    ...options,
  });
};

export const useUploadFile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: BodyUploadFileApiV1FilesUploadPost) => uploadFileApiV1FilesUploadPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

export const useDeleteFile = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteFileApiV1FilesFileIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
    },
  });
};

// ==================== Session Hooks ====================

export const useSessions = (
  params?: GetSessionsApiV1SessionsGetParams,
  options?: Omit<UseQueryOptions, 'queryKey' | 'queryFn'>
) => {
  return useQuery({
    queryKey: ['sessions', params],
    queryFn: () => getSessionsApiV1SessionsGet(params),
    ...options,
  });
};

export const useSession = (
  sessionId: number,
  options?: Omit<UseQueryOptions, 'queryKey' | 'queryFn'>
) => {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => getSessionApiV1SessionsSessionIdGet(sessionId),
    enabled: !!sessionId,
    ...options,
  });
};

export const useCreateSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AnalysisSessionCreate) => createSessionApiV1SessionsPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
};

export const useDeleteSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteSessionApiV1SessionsSessionIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
};

export const useArchiveSession = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => archiveSessionApiV1SessionsSessionIdArchivePost(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
};

// ==================== Message Hooks ====================

export const useMessages = (
  sessionId: number,
  params?: GetMessagesApiV1SessionsSessionIdMessagesGetParams,
  options?: Omit<UseQueryOptions, 'queryKey' | 'queryFn'>
) => {
  return useQuery({
    queryKey: ['messages', sessionId, params],
    queryFn: () => getMessagesApiV1SessionsSessionIdMessagesGet(sessionId, params),
    enabled: !!sessionId,
    ...options,
  });
};

export const useClearMessages = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: number) => clearMessagesApiV1SessionsSessionIdMessagesDelete(sessionId),
    onSuccess: (_data, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['messages', sessionId] });
    },
  });
};

// ==================== Recommendation Hooks ====================

export const useRecommendations = (
  sessionId: number,
  params?: GetRecommendationsApiV1SessionsSessionIdRecommendationsGetParams,
  options?: Omit<UseQueryOptions, 'queryKey' | 'queryFn'>
) => {
  return useQuery({
    queryKey: ['recommendations', sessionId, params],
    queryFn: () => getRecommendationsApiV1SessionsSessionIdRecommendationsGet(sessionId, params),
    enabled: !!sessionId,
    ...options,
  });
};

export const useGenerateRecommendations = (sessionId: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: GenerateRecommendationsApiV1SessionsSessionIdRecommendationsPostBody) =>
      generateRecommendationsApiV1SessionsSessionIdRecommendationsPost(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] });
    },
  });
};

export const useUpdateRecommendation = (sessionId: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: TaskRecommendationUpdate }) =>
      updateRecommendationApiV1SessionsSessionIdRecommendationsRecommendationIdPut(sessionId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] });
    },
  });
};

// 导出所有类型
export * from './fastDataAgent';


