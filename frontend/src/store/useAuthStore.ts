import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface UserInfo {
  userId: number;
  username: string;
  deptId: number;
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

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userInfo: null, 
      setToken: (token) => set({ token }),
      setUserInfo: (info) => set({ userInfo: info }),
      logout: () => {
        // 【对齐修复】登出时全量清理持久化及锁缓存
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (key?.startsWith('lock_token:')) {
                const docId = key.replace('lock_token:', '');
                const tokenVal = sessionStorage.getItem(key);
                if (tokenVal) {
                    // 静默释放锁
                    fetch(`/api/v1/locks/release?doc_id=${docId}&lock_token=${tokenVal}`, {
                        method: 'POST',
                        keepalive: true,
                        headers: { 'Authorization': `Bearer ${useAuthStore.getState().token}` }
                    }).catch(() => {});
                }
            }
        }
        set({ token: null, userInfo: null });
      },
    }),
    {
      name: 'taixing-nbs-auth-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
