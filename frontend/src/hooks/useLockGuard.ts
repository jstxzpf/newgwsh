import { useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { useEditorStore } from '../stores/editorStore';
import { message } from 'antd';

export function useLockGuard(docId: string | null) {
  const lockTokenRef = useRef<string | null>(null);
  const workerRef = useRef<Worker | null>(null);

  const releaseLock = () => {
    if (docId && lockTokenRef.current) {
      const content = useEditorStore.getState().content;
      // 容灾释放 (IRON RULE: use fetch with keepalive)
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

    // IRON RULE: must use Web Worker for heartbeat to avoid throttling
    workerRef.current = new Worker(new URL('./lockWorker.ts', import.meta.url), { type: 'module' });

    workerRef.current.onmessage = async (e) => {
      if (e.data.type === 'TICK' && lockTokenRef.current) {
        try {
          const res = await apiClient.post('/locks/heartbeat', { doc_id: docId, lock_token: lockTokenRef.current });
          const { next_suggested_heartbeat } = res.data.data;
          // 动态校准间隔
          workerRef.current?.postMessage({ type: 'START', interval: next_suggested_heartbeat * 1000 });
        } catch (err) {
          console.error("Heartbeat failed", err);
          workerRef.current?.postMessage({ type: 'STOP' });
        }
      }
    };

    const acquireLock = async () => {
      try {
        const res = await apiClient.post('/locks/acquire', { doc_id: docId });
        lockTokenRef.current = res.data.data.lock_token;
        // 初始心跳间隔 90s
        workerRef.current?.postMessage({ type: 'START', interval: 90000 });
      } catch (err: any) {
        if (err.response?.status === 423 || err.response?.data?.error_code === 'READONLY_CONFLICT') {
          message.warning('文档被占用，当前为只读模式');
        }
      }
    };

    acquireLock();

    const handleBeforeUnload = () => releaseLock();
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      if (workerRef.current) {
        workerRef.current.postMessage({ type: 'STOP' });
        workerRef.current.terminate();
      }
      releaseLock();
    };
  }, [docId]);

  return { lockToken: lockTokenRef.current };
}