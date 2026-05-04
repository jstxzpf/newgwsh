import { useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { useEditorStore } from '../stores/editorStore';
import { message } from 'antd';

export function useLockGuard(docId: string | null) {
  const lockTokenRef = useRef<string | null>(null);
  const timerRef = useRef<number | null>(null);

  const releaseLock = () => {
    if (docId && lockTokenRef.current) {
      const content = useEditorStore.getState().content;
      // 容灾释放
      fetch('/api/v1/locks/release', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ doc_id: docId, lock_token: lockTokenRef.current, content }),
        keepalive: true
      });
      lockTokenRef.current = null;
    }
  };

  useEffect(() => {
    if (!docId) return;

    const acquireLock = async () => {
      try {
        const res = await apiClient.post('/locks/acquire', { doc_id: docId });
        lockTokenRef.current = res.data.data.lock_token;
        startHeartbeat(180, 90);
      } catch (err: any) {
        if (err.response?.data?.error_code === 'READONLY_CONFLICT') {
          message.warning('文档被占用，当前为只读模式');
        }
      }
    };

    const startHeartbeat = (ttl: number, interval: number) => {
      if (timerRef.current) window.clearInterval(timerRef.current);
      timerRef.current = window.setInterval(async () => {
        if (!lockTokenRef.current) return;
        try {
          const res = await apiClient.post('/locks/heartbeat', { doc_id: docId, lock_token: lockTokenRef.current });
          const { next_suggested_heartbeat } = res.data.data;
          startHeartbeat(180, next_suggested_heartbeat);
        } catch (err) {
          // 心跳失败处理
          window.clearInterval(timerRef.current!);
        }
      }, interval * 1000);
    };

    acquireLock();

    const handleBeforeUnload = () => releaseLock();
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (timerRef.current) window.clearInterval(timerRef.current);
      releaseLock();
    };
  }, [docId]);

  return { lockToken: lockTokenRef.current };
}