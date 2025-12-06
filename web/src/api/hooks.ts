/**
 * API React Query Hooks
 * 封装生成的 API 函数为 React Query hooks
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { AxiosResponse } from 'axios';

// 导入 API 配置（初始化 axios 拦截器）
import './config';

// 导入类型
import type {
  AnalysisSessionCreate,
  BaseResponseAnalysisSessionDetail,
  BaseResponseAnalysisSessionResponse,
  BaseResponseDataSourceResponse,
  BaseResponseDataSourceSchemaResponse,
  BaseResponseDataSourceTestResult,
  BaseResponseInt,
  BaseResponseListTaskRecommendationResponse,
  BaseResponseNoneType,
  BaseResponsePageResponseAnalysisSessionResponse,
  BaseResponsePageResponseChatMessageResponse,
  BaseResponsePageResponseDataSourceResponse,
  BaseResponsePageResponseTaskRecommendationResponse,
  BaseResponsePageResponseUploadedFileResponse,
  BaseResponseTaskRecommendationResponse,
  // Response types
  BaseResponseToken,
  BaseResponseUploadedFileResponse,
  BaseResponseUserResponse,
  BodyUploadFileApiV1FilesUploadPost,
  DataSourceCreate,
  GenerateRecommendationsApiV1SessionsSessionIdRecommendationsPostBody,
  GetDataSourcesApiV1DataSourcesGetParams,
  GetMessagesApiV1SessionsSessionIdMessagesGetParams,
  GetRecommendationsApiV1SessionsSessionIdRecommendationsGetParams,
  GetSessionsApiV1SessionsGetParams,
  LoginRequest,
  TaskRecommendationUpdate,
  UserCreate,
} from './fastDataAgent';
// 导入生成的 API 函数
import {
  archiveSessionApiV1SessionsSessionIdArchivePost,
  clearMessagesApiV1SessionsSessionIdMessagesDelete,
  createDataSourceApiV1DataSourcesPost,
  createSessionApiV1SessionsPost,
  deleteDataSourceApiV1DataSourcesDataSourceIdDelete,
  deleteFileApiV1FilesFileIdDelete,
  deleteSessionApiV1SessionsSessionIdDelete,
  generateRecommendationsApiV1SessionsSessionIdRecommendationsPost,
  getCurrentUserInfoApiV1AuthMeGet,
  // Data Sources
  getDataSourcesApiV1DataSourcesGet,
  // Files
  getFilesApiV1FilesGet,
  // Messages
  getMessagesApiV1SessionsSessionIdMessagesGet,
  // Recommendations
  getRecommendationsApiV1SessionsSessionIdRecommendationsGet,
  getSessionApiV1SessionsSessionIdGet,
  // Sessions
  getSessionsApiV1SessionsGet,
  // Auth
  loginApiV1AuthLoginPost,
  registerApiV1AuthRegisterPost,
  syncDataSourceSchemaApiV1DataSourcesDataSourceIdSyncSchemaPost,
  testDataSourceConnectionApiV1DataSourcesDataSourceIdTestPost,
  updateRecommendationApiV1SessionsSessionIdRecommendationsRecommendationIdPut,
  uploadFileApiV1FilesUploadPost,
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
  return useMutation<AxiosResponse<BaseResponseAnalysisSessionResponse>, Error, AnalysisSessionCreate>({
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

export const useMessages = (sessionId: number, params?: GetMessagesApiV1SessionsSessionIdMessagesGetParams) => {
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
