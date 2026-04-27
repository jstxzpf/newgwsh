import { useEffect, useRef, useState } from 'react';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';
import { message } from 'antd';
import { appConfig } from '../config';
import { lockManager } from '../utils/lockManager';

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
        
        // 0. 尝试从 sessionStorage 恢复外部获取的锁 (如 Dashboard handleRevise 存入的)
        const savedToken = sessionStorage.getItem(`lock_token:${docId}`);
        
        // 1. 获取全局锁配置
        try {
          const confRes = await apiClient.get('/locks/config');
          hbInterval = (confRes.data.heartbeat_interval_seconds || 90) * 1000;
        } catch (e) {}

        if (savedToken) {
          lockTokenRef.current = savedToken;
          // 既然有了 Token，先做一次心跳验证
          try {
            await lockManager.heartbeat(docId, savedToken);
            setLockState('LOCKED');
            heartbeatTimer = window.setInterval(sendHeartbeat, hbInterval);
            return; // 成功恢复并验证
          } catch (e) {
            sessionStorage.removeItem(`lock_token:${docId}`); // Token 失效，继续走常规申请流程
          }
        }

        // 2. 申请锁 (常规流程：收口至 lockManager)
        const token = await lockManager.acquire(docId);
        
        lockTokenRef.current = token;
        setLockState('LOCKED');
        
        heartbeatTimer = window.setInterval(sendHeartbeat, hbInterval);
      } catch (error: any) {
        setLockState('READONLY_CONFLICT');
        // 【防吞噬修复】透明化报错
        if (error.response?.status !== 401) {
            message.error(error.response?.data?.detail || '获取编辑锁失败，现处于只读模式');
        }
      }
    };

    const sendHeartbeat = async () => {
      if (!lockTokenRef.current) return;
      try {
        await lockManager.heartbeat(docId, lockTokenRef.current);
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
        // 使用 lockManager 释放锁
        lockManager.release(docId, currentToken, true);
      }
    };
  }, [docId, userInfo]);

  return { lockState, lockToken: lockTokenRef.current };
};
