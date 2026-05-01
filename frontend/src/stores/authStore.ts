import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserInfo {
  user_id: number;
  username: string;
  full_name: string;
  role_level: number;
  dept_id: number;
  department_name: string;
}

interface AuthState {
  token: string | null;
  userInfo: UserInfo | null;
  setAuth: (token: string, userInfo: UserInfo) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userInfo: null,
      setAuth: (token, userInfo) => set({ token, userInfo }),
      clearAuth: () => set({ token: null, userInfo: null }),
    }),
    {
      name: 'taixing-auth-storage',
    }
  )
);
