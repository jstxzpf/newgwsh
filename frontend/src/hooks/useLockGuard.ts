import { useEffect, useRef, useState } from 'react';
import { lockService } from '../api/services';

export const useLockGuard = (docId: string | null) => {
  const [isReadOnly, setIsReadOnly] = useState(false);
  const [readOnlyReason, setReadOnlyReason] = useState<string | null>(null);
  const [lockToken, setLockToken] = useState<string | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const isAcquiring = useRef(false);

  useEffect(() => {
    if (!docId) return;

    // Initialize Web Worker for heartbeat
    workerRef.current = new Worker(new URL('../workers/heartbeatWorker.ts', import.meta.url), { type: 'module' });
    
    workerRef.current.onmessage = async (e) => {
      if (e.data.type === 'TICK' && lockToken && docId) {
        try {
          const res = await lockService.heartbeat({ doc_id: docId, lock_token: lockToken });
          // Update interval based on backend response
          if (res.next_suggested_heartbeat) {
            const nextInterval = res.next_suggested_heartbeat * 1000;
            workerRef.current?.postMessage({ type: 'UPDATE_INTERVAL', payload: { intervalMs: nextInterval } });
          }
        } catch (error) {
          console.error('Heartbeat failed', error);
          // If 423 or 409, lock might be lost
          setIsReadOnly(true);
          setReadOnlyReason('锁已失效，进入只读模式');
          stopHeartbeat();
        }
      }
    };

    return () => {
      releaseLock();
      if (workerRef.current) {
        workerRef.current.terminate();
      }
    };
  }, [docId, lockToken]);

  const acquireLock = async () => {
    if (!docId || isAcquiring.current || lockToken) return;
    
    isAcquiring.current = true;
    try {
      const res = await lockService.acquire({ doc_id: docId });
      setLockToken(res.lock_token);
      setIsReadOnly(false);
      setReadOnlyReason(null);
      
      // Start heartbeat
      workerRef.current?.postMessage({ 
        type: 'START', 
        payload: { intervalMs: 90000 } // Default, will update on first tick
      });
      
    } catch (error: any) {
      setIsReadOnly(true);
      if (error.response?.status === 409) {
        setReadOnlyReason('其他人正在编辑，当前只读');
      } else {
        setReadOnlyReason('公文状态不允许编辑');
      }
    } finally {
      isAcquiring.current = false;
    }
  };

  const releaseLock = () => {
    if (docId && lockToken) {
      stopHeartbeat();
      
      // Attempt clean release
      lockService.release({ doc_id: docId, lock_token: lockToken }).catch(() => {
        // Ignore errors on release, Redis will cleanup via TTL
      });
      setLockToken(null);
    }
  };

  const stopHeartbeat = () => {
    workerRef.current?.postMessage({ type: 'STOP' });
  };

  return {
    isReadOnly,
    readOnlyReason,
    acquireLock,
    releaseLock,
    lockToken,
  };
};
