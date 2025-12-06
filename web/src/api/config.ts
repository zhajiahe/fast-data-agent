/**
 * API 配置
 * 为生成的 API 客户端配置 axios 默认值
 */
import axios from 'axios';
import { storage } from '@/utils/storage';

// 配置 axios 默认值
axios.defaults.baseURL = import.meta.env.VITE_API_BASE_URL || '';
axios.defaults.timeout = 30000;
// 注意：不要设置全局 Content-Type，让 axios 根据数据类型自动设置
// 如果设置为 application/json，会导致 FormData 文件上传失败

// 请求拦截器 - 添加认证头
axios.interceptors.request.use(
  (config) => {
    const token = storage.getToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 处理认证错误
axios.interceptors.response.use(
  (response) => {
    // 处理统一响应格式
    if (response.data && response.data.success === false) {
      const error: Error & { response?: unknown } = new Error(response.data.msg || '请求失败');
      error.response = response;
      return Promise.reject(error);
    }
    return response;
  },
  (error) => {
    // 处理 401 认证错误
    if (error.response?.status === 401) {
      storage.clearAuth();
      const currentPath = window.location.pathname;
      if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
        // 使用 BASE_URL 构建正确的登录路径
        const basePath = (import.meta.env.VITE_BASE_PATH || import.meta.env.BASE_URL || '/').replace(/\/$/, '') || '';
        window.location.href = `${basePath}/login`;
      }
    }

    // 增强错误信息
    if (error.response?.data?.msg) {
      error.message = error.response.data.msg;
    }

    return Promise.reject(error);
  }
);

export default axios;
