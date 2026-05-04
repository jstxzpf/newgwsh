import { create } from 'zustand'

interface UserInfo {
  user_id: number;
  username: string;
  full_name: string;
  role_level: number;
  dept_id: number | null;
}

interface AuthState {
  token: string | null;
  userInfo: UserInfo | null;
  setToken: (token: string | null) => void;
  setUserInfo: (info: UserInfo | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('access_token'),
  userInfo: null,
  setToken: (token) => {
    if (token) localStorage.setItem('access_token', token);
    else localStorage.removeItem('access_token');
    set({ token })
  },
  setUserInfo: (info) => set({ userInfo: info }),
  logout: () => {
    localStorage.removeItem('access_token');
    set({ token: null, userInfo: null });
    window.location.href = '/login';
  }
}))