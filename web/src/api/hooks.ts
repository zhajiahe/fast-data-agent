/**
 * API React Query Hooks
 * 封装生成的 API 函数为 React Query hooks
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  // Response types
  BaseResponseToken,
  BaseResponseUserResponse,
  BaseResponsePageResponseDataSourceResponse,
  BaseResponseDataSourceResponse,
  BaseResponseDataSourceTestResult,
  BaseResponseDataSourceSchemaResponse,
  BaseResponsePageResponseUploadedFileResponse,
  BaseResponseUploadedFileResponse,
  BaseResponsePageResponseAnalysisSessionResponse,
  BaseResponseAnalysisSessionDetail,
  BaseResponseAnalysisSessionResponse,
  BaseResponseNoneType,
  BaseResponseInt,
  BaseResponsePageResponseChatMessageResponse,
  BaseResponsePageResponseTaskRecommendationResponse,
  BaseResponseListTaskRecommendationResponse,
  BaseResponseTaskRecommendationResponse,
} from './fastDataAgent';

// ==================== Auth Hooks ====================

export const useLogin = () => {
  return useMutation<AxiosResponse<BaseResponseToken>, Error, LoginRequest>({
    mutationFn: (data) => loginApiV1AuthLoginPost(data),
  });
};

export const useRegister = () => {
  return useMutation<AxiosResponse<BaseResponseUserResponse>, Error, UserCreate>({
    mutationFn: (data) => registerApiV1AuthRegisterPost(data),
  });
};

export const useCurrentUser = () => {
  return useQuery<AxiosResponse<BaseResponseUserResponse>, Error>({
    queryKey: ['currentUser'],
    queryFn: () => getCurrentUserInfoApiV1AuthMeGet(),
  });
};

// ==================== Data Source Hooks ====================

export const useDataSources = (params?: GetDataSourcesApiV1DataSourcesGetParams) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseDataSourceResponse>, Error>({
    queryKey: ['dataSources', params],
    queryFn: () => getDataSourcesApiV1DataSourcesGet(params),
  });
};

export const useCreateDataSource = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseDataSourceResponse>, Error, DataSourceCreate>({
    mutationFn: (data) => createDataSourceApiV1DataSourcesPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

export const useDeleteDataSource = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseNoneType>, Error, number>({
    mutationFn: (id) => deleteDataSourceApiV1DataSourcesDataSourceIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

export const useTestDataSourceConnection = () => {
  return useMutation<AxiosResponse<BaseResponseDataSourceTestResult>, Error, number>({
    mutationFn: (id) => testDataSourceConnectionApiV1DataSourcesDataSourceIdTestPost(id),
  });
};

export const useSyncDataSourceSchema = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseDataSourceSchemaResponse>, Error, number>({
    mutationFn: (id) => syncDataSourceSchemaApiV1DataSourcesDataSourceIdSyncSchemaPost(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

// ==================== File Hooks ====================

export const useFiles = () => {
  return useQuery<AxiosResponse<BaseResponsePageResponseUploadedFileResponse>, Error>({
    queryKey: ['files'],
    queryFn: () => getFilesApiV1FilesGet(),
  });
};

export const useUploadFile = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseUploadedFileResponse>, Error, BodyUploadFileApiV1FilesUploadPost>({
    mutationFn: (data) => uploadFileApiV1FilesUploadPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

export const useDeleteFile = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseNoneType>, Error, number>({
    mutationFn: (id) => deleteFileApiV1FilesFileIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
    },
  });
};

// ==================== Session Hooks ====================

export const useSessions = (params?: GetSessionsApiV1SessionsGetParams) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseAnalysisSessionResponse>, Error>({
    queryKey: ['sessions', params],
    queryFn: () => getSessionsApiV1SessionsGet(params),
  });
};

export const useSession = (sessionId: number) => {
  return useQuery<AxiosResponse<BaseResponseAnalysisSessionDetail>, Error>({
    queryKey: ['session', sessionId],
    queryFn: () => getSessionApiV1SessionsSessionIdGet(sessionId),
    enabled: !!sessionId,
  });
};

export const useCreateSession = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseAnalysisSessionDetail>, Error, AnalysisSessionCreate>({
    mutationFn: (data) => createSessionApiV1SessionsPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
};

export const useDeleteSession = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseNoneType>, Error, number>({
    mutationFn: (id) => deleteSessionApiV1SessionsSessionIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
};

export const useArchiveSession = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseAnalysisSessionResponse>, Error, number>({
    mutationFn: (id) => archiveSessionApiV1SessionsSessionIdArchivePost(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
};

// ==================== Message Hooks ====================

export const useMessages = (
  sessionId: number,
  params?: GetMessagesApiV1SessionsSessionIdMessagesGetParams
) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseChatMessageResponse>, Error>({
    queryKey: ['messages', sessionId, params],
    queryFn: () => getMessagesApiV1SessionsSessionIdMessagesGet(sessionId, params),
    enabled: !!sessionId,
  });
};

export const useClearMessages = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseInt>, Error, number>({
    mutationFn: (sessionId) => clearMessagesApiV1SessionsSessionIdMessagesDelete(sessionId),
    onSuccess: (_data, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['messages', sessionId] });
    },
  });
};

// ==================== Recommendation Hooks ====================

export const useRecommendations = (
  sessionId: number,
  params?: GetRecommendationsApiV1SessionsSessionIdRecommendationsGetParams
) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseTaskRecommendationResponse>, Error>({
    queryKey: ['recommendations', sessionId, params],
    queryFn: () => getRecommendationsApiV1SessionsSessionIdRecommendationsGet(sessionId, params),
    enabled: !!sessionId,
  });
};

export const useGenerateRecommendations = (sessionId: number) => {
  const queryClient = useQueryClient();
  return useMutation<
    AxiosResponse<BaseResponseListTaskRecommendationResponse>,
    Error,
    GenerateRecommendationsApiV1SessionsSessionIdRecommendationsPostBody
  >({
    mutationFn: (data) => generateRecommendationsApiV1SessionsSessionIdRecommendationsPost(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] });
    },
  });
};

export const useUpdateRecommendation = (sessionId: number) => {
  const queryClient = useQueryClient();
  return useMutation<
    AxiosResponse<BaseResponseTaskRecommendationResponse>,
    Error,
    { id: number; data: TaskRecommendationUpdate }
  >({
    mutationFn: ({ id, data }) =>
      updateRecommendationApiV1SessionsSessionIdRecommendationsRecommendationIdPut(sessionId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] });
    },
  });
};

// 导出所有类型
export * from './fastDataAgent';
