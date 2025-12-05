/**
 * 本地存储工具类
 */

export const storage = {
  // 获取 token
  getToken: () => localStorage.getItem('access_token'),

  // 设置 token
  setToken: (token: string) => localStorage.setItem('access_token', token),

  // 移除 token
  removeToken: () => localStorage.removeItem('access_token'),

  // 获取 refresh token
  getRefreshToken: () => localStorage.getItem('refresh_token'),

  // 设置 refresh token
  setRefreshToken: (token: string) => localStorage.setItem('refresh_token', token),

  // 移除 refresh token
  removeRefreshToken: () => localStorage.removeItem('refresh_token'),

  // 获取用户信息
  getUser: () => {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  },

  // 设置用户信息
  setUser: (user: any) => localStorage.setItem('user', JSON.stringify(user)),

  // 移除用户信息
  removeUser: () => localStorage.removeItem('user'),

  // 清除所有认证信息
  clearAuth: () => {
    storage.removeToken();
    storage.removeRefreshToken();
    storage.removeUser();
  },
};
