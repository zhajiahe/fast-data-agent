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
  is_active?: boolean;
  is_superuser?: boolean;
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
    // 注意：不在这里跳转，让调用者使用 react-router 的 navigate
    // 这样可以正确处理 basename
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
