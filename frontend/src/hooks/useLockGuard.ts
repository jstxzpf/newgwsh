import { useEffect, useRef, useState } from 'react';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';
import { message } from 'antd';

export type LockState = 'ACQUIRING' | 'LOCKED' | 'READONLY_CONFLICT';

export const useLockGuard = (docId: string | null) => {
  const [lockState, setLockState] = useState<LockState>('ACQUIRING');
  const lockTokenRef = useRef<string | null>(null);
  const userInfo = useAuthStore(state => state.userInfo);

  useEffect(() => {
    if (!docId || !userInfo) return;

    let heartbeatTimer: number;
    let hbInterval = 90000;

    const acquireLock = async () => {
      try {
        setLockState('ACQUIRING');
        // 1. 获取全局锁配置
        const confRes = await apiClient.get('/locks/config');
        hbInterval = (confRes.data.heartbeat_interval_seconds || 90) * 1000;

        // 2. 申请锁
        const res = await apiClient.post(`/documents/${docId}/lock`, null, {
          params: { user_id: userInfo.userId, username: userInfo.username }
        });
        
        lockTokenRef.current = res.data.lock_token;
        setLockState('LOCKED');
        
        heartbeatTimer = window.setInterval(sendHeartbeat, hbInterval);
      } catch (error: any) {
        setLockState('READONLY_CONFLICT');
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
          message.warning('锁续期失败或已遗失，现处于只读模式。');
        }
      }
    };

    acquireLock();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && lockTokenRef.current) {
        sendHeartbeat(); // 页面重获焦点时立即探活
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(heartbeatTimer);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      
      const currentToken = lockTokenRef.current;
      if (currentToken) {
        // 构造完整的 URL 与 Headers，防跨域截断 (修复点：显式传递凭证)
        const authHeader = `Bearer ${useAuthStore.getState().token || ''}`;
        fetch(`/api/v1/documents/${docId}/unlock?lock_token=${currentToken}`, {
          method: 'POST',
          keepalive: true,
          headers: {
            'Authorization': authHeader,
            'Content-Type': 'application/json'
          }
        }).catch(() => {}); // 静默处理
      }
    };
  }, [docId, userInfo]);

  return { lockState };
};
