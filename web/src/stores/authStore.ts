import { create } from 'zustand';
import { storage } from '@/utils/storage';

/**
 * 用户信息类型
 * 根据实际后端返回格式调整
 */
export interface User {
  id: string;
  username: string;
  nickname?: string;
  email?: string;
  avatar?: string;
  [key: string]: any;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  // Actions
  setAuth: (user: User, token: string, refreshToken: string) => void;
  clearAuth: () => void;
  logout: () => void;
  updateUser: (user: User) => void;
  initAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  setAuth: (user, token, refreshToken) => {
    storage.setToken(token);
    storage.setRefreshToken(refreshToken);
    storage.setUser(user);
    set({ user, token, isAuthenticated: true });
  },

  clearAuth: () => {
    storage.clearAuth();
    set({ user: null, token: null, isAuthenticated: false });
  },

  logout: () => {
    storage.clearAuth();
    set({ user: null, token: null, isAuthenticated: false });
    // 跳转到登录页
    window.location.href = '/login';
  },

  updateUser: (user) => {
    storage.setUser(user);
    set({ user });
  },

  initAuth: () => {
    const token = storage.getToken();
    const user = storage.getUser();
    if (token && user) {
      set({ user, token, isAuthenticated: true });
    }
  },
}));
