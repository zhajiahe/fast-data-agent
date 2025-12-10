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
  BaseResponseDatabaseConnectionTablesResponse,
  BaseResponseDatabaseTableSchemaResponse,
  BaseResponseDataSourcePreviewResponse,
  BaseResponseDataSourceResponse,
  BaseResponseFilePreviewResponse,
  BaseResponseInt,
  BaseResponseListTaskRecommendationResponse,
  BaseResponseNoneType,
  BaseResponsePageResponseAnalysisSessionResponse,
  BaseResponsePageResponseChatMessageResponse,
  BaseResponsePageResponseDatabaseConnectionResponse,
  BaseResponsePageResponseDataSourceResponse,
  BaseResponsePageResponseRawDataResponse,
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
  GetConnectionsApiV1DatabaseConnectionsGetParams,
  GetConnectionTableSchemaApiV1DatabaseConnectionsConnectionIdSchemaGetParams,
  GetDataSourcesApiV1DataSourcesGetParams,
  GetFilePreviewApiV1FilesFileIdPreviewGetParams,
  GetMessagesApiV1SessionsSessionIdMessagesGetParams,
  GetRawDataListApiV1RawDataGetParams,
  GetRecommendationsApiV1SessionsSessionIdRecommendationsGetParams,
  GetSessionsApiV1SessionsGetParams,
  LoginRequest,
  PreviewDataSourceApiV1DataSourcesDataSourceIdPreviewPostBody,
  TaskRecommendationUpdate,
  UserCreate,
} from './fastDataAgent';
// 导入生成的 API 函数
import {
  archiveSessionApiV1SessionsSessionIdArchivePost,
  clearMessagesApiV1SessionsSessionIdMessagesDelete,
  createDataSourceApiV1DataSourcesPost,
  createSessionApiV1SessionsPost,
  deleteConnectionApiV1DatabaseConnectionsConnectionIdDelete,
  deleteDataSourceApiV1DataSourcesDataSourceIdDelete,
  deleteFileApiV1FilesFileIdDelete,
  deleteSessionApiV1SessionsSessionIdDelete,
  generateRecommendationsApiV1SessionsSessionIdRecommendationsPost,
  getConnectionsApiV1DatabaseConnectionsGet,
  getConnectionTableSchemaApiV1DatabaseConnectionsConnectionIdSchemaGet,
  getConnectionTablesApiV1DatabaseConnectionsConnectionIdTablesGet,
  getCurrentUserInfoApiV1AuthMeGet,
  // Data Sources
  getDataSourcesApiV1DataSourcesGet,
  // Files
  getFilePreviewApiV1FilesFileIdPreviewGet,
  getFilesApiV1FilesGet,
  // Messages
  getMessagesApiV1SessionsSessionIdMessagesGet,
  // RawData
  getRawDataListApiV1RawDataGet,
  // Recommendations
  getRecommendationsApiV1SessionsSessionIdRecommendationsGet,
  getSessionApiV1SessionsSessionIdGet,
  // Sessions
  getSessionsApiV1SessionsGet,
  // Auth
  loginApiV1AuthLoginPost,
  previewDataSourceApiV1DataSourcesDataSourceIdPreviewPost,
  refreshDataSourceSchemaApiV1DataSourcesDataSourceIdRefreshSchemaPost,
  registerApiV1AuthRegisterPost,
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

export const useSyncDataSourceSchema = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseDataSourceResponse>, Error, number>({
    mutationFn: (id) => refreshDataSourceSchemaApiV1DataSourcesDataSourceIdRefreshSchemaPost(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataSources'] });
    },
  });
};

export const useDataSourcePreview = (
  dataSourceId?: number,
  body: PreviewDataSourceApiV1DataSourcesDataSourceIdPreviewPostBody = {}
) => {
  return useQuery<AxiosResponse<BaseResponseDataSourcePreviewResponse>, Error>({
    queryKey: ['data-source-preview', dataSourceId, body],
    queryFn: () => previewDataSourceApiV1DataSourcesDataSourceIdPreviewPost(dataSourceId as number, body),
    enabled: !!dataSourceId,
  });
};

// ==================== RawData Hooks ====================

export const useRawDataList = (params?: GetRawDataListApiV1RawDataGetParams) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseRawDataResponse>, Error>({
    queryKey: ['rawData', params],
    queryFn: () => getRawDataListApiV1RawDataGet(params),
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

export const useDeleteDbConnection = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseNoneType>, Error, number>({
    mutationFn: (id) => deleteConnectionApiV1DatabaseConnectionsConnectionIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['db-connections'] });
    },
  });
};

export const useFilePreview = (fileId: number, params?: GetFilePreviewApiV1FilesFileIdPreviewGetParams) => {
  return useQuery<AxiosResponse<BaseResponseFilePreviewResponse>, Error>({
    queryKey: ['filePreview', fileId, params],
    queryFn: () => getFilePreviewApiV1FilesFileIdPreviewGet(fileId, params),
    enabled: !!fileId,
  });
};

// ==================== Database Connections ====================

export const useDbConnections = (params?: GetConnectionsApiV1DatabaseConnectionsGetParams) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseDatabaseConnectionResponse>, Error>({
    queryKey: ['db-connections', params],
    queryFn: () => getConnectionsApiV1DatabaseConnectionsGet(params),
  });
};

export const useDbTables = (connectionId?: number) => {
  return useQuery<AxiosResponse<BaseResponseDatabaseConnectionTablesResponse>, Error>({
    queryKey: ['db-tables', connectionId],
    queryFn: () => getConnectionTablesApiV1DatabaseConnectionsConnectionIdTablesGet(connectionId as number),
    enabled: !!connectionId,
  });
};

export const useDbTableSchema = (
  connectionId?: number,
  params?: GetConnectionTableSchemaApiV1DatabaseConnectionsConnectionIdSchemaGetParams
) => {
  return useQuery<AxiosResponse<BaseResponseDatabaseTableSchemaResponse>, Error>({
    queryKey: ['db-table-schema', connectionId, params],
    queryFn: () =>
      getConnectionTableSchemaApiV1DatabaseConnectionsConnectionIdSchemaGet(connectionId as number, params),
    enabled: !!connectionId && !!params?.table_name,
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

// 类型通过 api/index.ts 从 fastDataAgent.ts 导出
