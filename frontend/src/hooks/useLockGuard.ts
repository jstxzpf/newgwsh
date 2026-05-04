import { useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { useEditorStore } from '../stores/editorStore';
import { message } from 'antd';

export function useLockGuard(docId: string | null) {
  const lockTokenRef = useRef<string | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const setReadOnly = useEditorStore(state => state.setReadOnly);
  const setLockTTL = useEditorStore(state => state.setLockTTL);

  const releaseLock = () => {
    if (docId && lockTokenRef.current) {
      const content = useEditorStore.getState().content;
      // 容灾释放铁律 (§七.2): fetch + keepalive + 原子合并
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
const acquireLock = async () => {
  if (!docId) return;
  try {
    // 1. 获取动态配置 (§五.5)
    const configRes = await apiClient.get('/locks/config');
    const { lock_ttl_seconds, heartbeat_interval_seconds } = configRes.data.data;

    // 2. 申请锁
    const res = await apiClient.post('/locks/acquire', { doc_id: docId });
    lockTokenRef.current = res.data.data.lock_token;

    setReadOnly(false);
    setLockTTL(lock_ttl_seconds);

    // 3. 启动 Web Worker
    workerRef.current?.postMessage({ 
      type: 'START', 
      interval: heartbeat_interval_seconds * 1000 
    });
  } catch (err: any) {
...
      // 刚性控制 (§七.2)：锁获取失败 409/423 触发只读
      if (err.response?.status === 409 || err.response?.status === 423) {
        setReadOnly(true, 'CONFLICT');
      }
    }
  };

  useEffect(() => {
    if (!docId) return;

    // 铁律 (§八.8)：Web Worker 心跳防节流
    workerRef.current = new Worker(new URL('./lockWorker.ts', import.meta.url), { type: 'module' });

    workerRef.current.onmessage = async (e) => {
      if (e.data.type === 'TICK' && lockTokenRef.current) {
        try {
          const res = await apiClient.post('/locks/heartbeat', { doc_id: docId, lock_token: lockTokenRef.current });
          const { next_suggested_heartbeat, lock_ttl_remaining } = res.data.data;
          setLockTTL(lock_ttl_remaining);
          workerRef.current?.postMessage({ type: 'START', interval: next_suggested_heartbeat * 1000 });
        } catch (err) {
          setReadOnly(true, 'CONFLICT');
          workerRef.current?.postMessage({ type: 'STOP' });
        }
      }
    };

    // 延时预占铁律 (§七.2)：新建不占锁，输入时占 (这里简化为进入即试，输入占由 Editor 组件负责更佳)
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

  return { lockToken: lockTokenRef.current, reacquire: acquireLock };
}