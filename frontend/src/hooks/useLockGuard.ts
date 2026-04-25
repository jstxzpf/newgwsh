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
        // 1. 获取全局锁配置 (颗粒度对齐)
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

    // 3. 休眠/不可见状态唤醒校验 (颗粒度对齐)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && lockTokenRef.current) {
        sendHeartbeat(); // 页面重获焦点时立即探活
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      clearInterval(heartbeatTimer);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (lockTokenRef.current) {
        fetch(`/api/v1/documents/${docId}/unlock?lock_token=${lockTokenRef.current}`, {
          method: 'POST',
          keepalive: true
        }).catch(console.error);
      }
    };
  }, [docId, userInfo]);

  return { lockState };
};
