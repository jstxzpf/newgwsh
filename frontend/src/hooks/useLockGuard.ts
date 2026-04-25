import { useEffect, useRef, useState } from 'react';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';

export type LockState = 'ACQUIRING' | 'LOCKED' | 'READONLY_CONFLICT';

export const useLockGuard = (docId: string | null) => {
  const [lockState, setLockState] = useState<LockState>('ACQUIRING');
  const lockTokenRef = useRef<string | null>(null);
  const userInfo = useAuthStore(state => state.userInfo);

  useEffect(() => {
    if (!docId || !userInfo) return;

    let heartbeatTimer: number;

    const acquireLock = async () => {
      try {
        setLockState('ACQUIRING');
        const res = await apiClient.post(`/documents/${docId}/lock`, null, {
          params: {
            user_id: userInfo.userId,
            username: userInfo.username
          }
        });
        lockTokenRef.current = res.data.lock_token;
        setLockState('LOCKED');
        
        // 启动心跳 (90秒)
        heartbeatTimer = window.setInterval(sendHeartbeat, 90000);
      } catch (error: any) {
        if (error.response?.status === 409) {
          setLockState('READONLY_CONFLICT');
        } else {
          setLockState('READONLY_CONFLICT');
          console.error("Failed to acquire lock:", error);
        }
      }
    };

    const sendHeartbeat = async () => {
      if (!lockTokenRef.current) return;
      try {
        await apiClient.post(`/documents/${docId}/heartbeat`, null, {
          params: { lock_token: lockTokenRef.current }
        });
      } catch (error: any) {
        if (error.response?.status === 409) {
          setLockState('READONLY_CONFLICT');
          clearInterval(heartbeatTimer);
        }
      }
    };

    acquireLock();

    return () => {
      clearInterval(heartbeatTimer);
      if (lockTokenRef.current) {
        // 使用 fetch keepalive 保证页面卸载时请求能发出去
        fetch(`/api/v1/documents/${docId}/unlock?lock_token=${lockTokenRef.current}`, {
          method: 'POST',
          keepalive: true
        }).catch(console.error);
      }
    };
  }, [docId, userInfo]);

  return { lockState };
};
