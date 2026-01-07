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
  BaseResponseDatabaseConnectionWithRawResponse,
  BaseResponseDatabaseTableSchemaResponse,
  BaseResponseFilePreviewResponse,
  BaseResponseInt,
  BaseResponseListTaskRecommendationResponse,
  BaseResponseNoneType,
  BaseResponsePageResponseAnalysisSessionResponse,
  BaseResponsePageResponseChatMessageResponse,
  BaseResponsePageResponseDatabaseConnectionResponse,
  BaseResponsePageResponseRawDataResponse,
  BaseResponsePageResponseTaskRecommendationResponse,
  BaseResponsePageResponseUploadedFileResponse,
  BaseResponseRawDataPreviewResponse,
  BaseResponseRawDataResponse,
  BaseResponseTaskRecommendationResponse,
  // Response types
  BaseResponseToken,
  BaseResponseUploadedFileResponse,
  BaseResponseUserResponse,
  BodyUploadFileApiV1FilesUploadPost,
  CreateConnectionApiV1DatabaseConnectionsPostParams,
  DatabaseConnectionCreate,
  GenerateRecommendationsApiV1SessionsSessionIdRecommendationsPostBody,
  GetConnectionsApiV1DatabaseConnectionsGetParams,
  GetConnectionTableSchemaApiV1DatabaseConnectionsConnectionIdSchemaGetParams,
  GetFilePreviewApiV1FilesFileIdPreviewGetParams,
  GetMessagesApiV1SessionsSessionIdMessagesGetParams,
  GetRawDataListApiV1RawDataGetParams,
  GetRecommendationsApiV1SessionsSessionIdRecommendationsGetParams,
  GetSessionsApiV1SessionsGetParams,
  LoginRequest,
  PreviewRawDataApiV1RawDataRawDataIdPreviewPostBody,
  RawDataCreate,
  TaskRecommendationUpdate,
  UserCreate,
} from './fastDataAgent';
// 导入生成的 API 函数
import {
  archiveSessionApiV1SessionsSessionIdArchivePost,
  clearMessagesApiV1SessionsSessionIdMessagesDelete,
  createConnectionApiV1DatabaseConnectionsPost,
  // RawData
  createRawDataApiV1RawDataPost,
  createSessionApiV1SessionsPost,
  deleteConnectionApiV1DatabaseConnectionsConnectionIdDelete,
  deleteFileApiV1FilesFileIdDelete,
  deleteSessionApiV1SessionsSessionIdDelete,
  generateRecommendationsApiV1SessionsSessionIdRecommendationsPost,
  getConnectionsApiV1DatabaseConnectionsGet,
  getConnectionTableSchemaApiV1DatabaseConnectionsConnectionIdSchemaGet,
  getConnectionTablesApiV1DatabaseConnectionsConnectionIdTablesGet,
  getCurrentUserInfoApiV1AuthMeGet,
  // Files
  getFilePreviewApiV1FilesFileIdPreviewGet,
  getFilesApiV1FilesGet,
  // Messages
  getMessagesApiV1SessionsSessionIdMessagesGet,
  getRawDataListApiV1RawDataGet,
  // Recommendations
  getRecommendationsApiV1SessionsSessionIdRecommendationsGet,
  getSessionApiV1SessionsSessionIdGet,
  // Sessions
  getSessionsApiV1SessionsGet,
  // Auth
  loginApiV1AuthLoginPost,
  previewRawDataApiV1RawDataRawDataIdPreviewPost,
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

// ==================== RawData Hooks ====================

export const useRawDataList = (params?: GetRawDataListApiV1RawDataGetParams) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseRawDataResponse>, Error>({
    queryKey: ['rawData', params],
    queryFn: () => getRawDataListApiV1RawDataGet(params),
  });
};

export const useCreateRawData = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseRawDataResponse>, Error, RawDataCreate>({
    mutationFn: (data) => createRawDataApiV1RawDataPost(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rawData'] });
    },
  });
};

export const useRawDataPreview = (
  rawDataId?: string,
  body: PreviewRawDataApiV1RawDataRawDataIdPreviewPostBody = {}
) => {
  return useQuery<AxiosResponse<BaseResponseRawDataPreviewResponse>, Error>({
    queryKey: ['rawDataPreview', rawDataId, body],
    queryFn: () => previewRawDataApiV1RawDataRawDataIdPreviewPost(rawDataId as string, body),
    enabled: !!rawDataId,
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
      queryClient.invalidateQueries({ queryKey: ['rawData'] });
    },
  });
};

export const useDeleteFile = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseNoneType>, Error, string>({
    mutationFn: (id) => deleteFileApiV1FilesFileIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['files'] });
      queryClient.invalidateQueries({ queryKey: ['rawData'] });
    },
  });
};

export const useFilePreview = (fileId: string, params?: GetFilePreviewApiV1FilesFileIdPreviewGetParams) => {
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

export const useCreateDbConnection = () => {
  const queryClient = useQueryClient();
  return useMutation<
    AxiosResponse<BaseResponseDatabaseConnectionWithRawResponse>,
    Error,
    { data: DatabaseConnectionCreate; params?: CreateConnectionApiV1DatabaseConnectionsPostParams }
  >({
    mutationFn: ({ data, params }) => createConnectionApiV1DatabaseConnectionsPost(data, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['db-connections'] });
      queryClient.invalidateQueries({ queryKey: ['rawData'] });
    },
  });
};

export const useDeleteDbConnection = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseNoneType>, Error, string>({
    mutationFn: (id) => deleteConnectionApiV1DatabaseConnectionsConnectionIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['db-connections'] });
      queryClient.invalidateQueries({ queryKey: ['rawData'] });
    },
  });
};

export const useDbTables = (connectionId?: string) => {
  return useQuery<AxiosResponse<BaseResponseDatabaseConnectionTablesResponse>, Error>({
    queryKey: ['db-tables', connectionId],
    queryFn: () => getConnectionTablesApiV1DatabaseConnectionsConnectionIdTablesGet(connectionId as string),
    enabled: !!connectionId,
  });
};

export const useDbTableSchema = (
  connectionId?: string,
  params?: GetConnectionTableSchemaApiV1DatabaseConnectionsConnectionIdSchemaGetParams
) => {
  return useQuery<AxiosResponse<BaseResponseDatabaseTableSchemaResponse>, Error>({
    queryKey: ['db-table-schema', connectionId, params],
    queryFn: () =>
      getConnectionTableSchemaApiV1DatabaseConnectionsConnectionIdSchemaGet(connectionId as string, params),
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

export const useSession = (sessionId: string) => {
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
  return useMutation<AxiosResponse<BaseResponseNoneType>, Error, string>({
    mutationFn: (id) => deleteSessionApiV1SessionsSessionIdDelete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
};

export const useArchiveSession = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseAnalysisSessionResponse>, Error, string>({
    mutationFn: (id) => archiveSessionApiV1SessionsSessionIdArchivePost(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
};

// ==================== Message Hooks ====================

export const useMessages = (sessionId: string, params?: GetMessagesApiV1SessionsSessionIdMessagesGetParams) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseChatMessageResponse>, Error>({
    queryKey: ['messages', sessionId, params],
    queryFn: () => getMessagesApiV1SessionsSessionIdMessagesGet(sessionId, params),
    enabled: !!sessionId,
  });
};

export const useClearMessages = () => {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<BaseResponseInt>, Error, string>({
    mutationFn: (sessionId) => clearMessagesApiV1SessionsSessionIdMessagesDelete(sessionId),
    onSuccess: (_data, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['messages', sessionId] });
    },
  });
};

// ==================== Recommendation Hooks ====================

export const useRecommendations = (
  sessionId: string,
  params?: GetRecommendationsApiV1SessionsSessionIdRecommendationsGetParams
) => {
  return useQuery<AxiosResponse<BaseResponsePageResponseTaskRecommendationResponse>, Error>({
    queryKey: ['recommendations', sessionId, params],
    queryFn: () => getRecommendationsApiV1SessionsSessionIdRecommendationsGet(sessionId, params),
    enabled: !!sessionId,
  });
};

export const useGenerateRecommendations = (sessionId: string) => {
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

export const useUpdateRecommendation = (sessionId: string) => {
  const queryClient = useQueryClient();
  return useMutation<
    AxiosResponse<BaseResponseTaskRecommendationResponse>,
    Error,
    { id: string; data: TaskRecommendationUpdate }
  >({
    mutationFn: ({ id, data }) =>
      updateRecommendationApiV1SessionsSessionIdRecommendationsRecommendationIdPut(sessionId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] });
    },
  });
};

// 类型通过 api/index.ts 从 fastDataAgent.ts 导出
