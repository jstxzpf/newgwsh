import { create } from 'zustand';

interface UserInfo {
  userId: number;
  username: string;
  deptName: string;
  roleLevel: number;
}

interface AuthState {
  token: string | null;
  userInfo: UserInfo | null;
  setToken: (token: string) => void;
  setUserInfo: (info: UserInfo) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  userInfo: { userId: 1, username: '测试科员', deptName: '综合科', roleLevel: 1 }, // 模拟初始状态
  setToken: (token) => set({ token }),
  setUserInfo: (info) => set({ userInfo: info }),
  logout: () => set({ token: null, userInfo: null }),
}));
