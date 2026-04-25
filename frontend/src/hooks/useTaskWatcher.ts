import { useEffect, useRef, useState } from 'react';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';

export type TaskStatus = 'IDLE' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export const useTaskWatcher = () => {
  const [taskStatus, setTaskStatus] = useState<TaskStatus>('IDLE');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<string | null>(null);
  const userInfo = useAuthStore(state => state.userInfo);
  
  const activeEventSource = useRef<EventSource | null>(null);

  const watchTask = async (taskId: string, onComplete?: (res: string) => void) => {
    if (!userInfo) return;
    
    setTaskStatus('QUEUED');
    setProgress(0);

    try {
      // 1. 换取 Ticket
      const ticketRes = await apiClient.post('/sse/ticket', null, {
        params: { task_id: taskId, user_id: userInfo.userId }
      });
      const ticket = ticketRes.data.ticket;

      // 2. 建立 SSE 连接
      const es = new EventSource(`/api/v1/sse/${taskId}/events?ticket=${ticket}`);
      activeEventSource.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setProgress(data.progress);
          setTaskStatus(data.status);
          
          if (data.status === 'COMPLETED') {
            setResult(data.result);
            es.close();
            if (onComplete && data.result) onComplete(data.result);
          } else if (data.status === 'FAILED') {
            es.close();
          }
        } catch (e) {
          console.error('Failed to parse SSE event:', e);
        }
      };

      es.onerror = (err) => {
        console.error('SSE connection error:', err);
        es.close();
        setTaskStatus('FAILED');
      };
      
    } catch (err) {
      console.error('Failed to get SSE ticket:', err);
      setTaskStatus('FAILED');
    }
  };

  useEffect(() => {
    return () => {
      if (activeEventSource.current) {
        activeEventSource.current.close();
      }
    };
  }, []);

  return { taskStatus, progress, result, watchTask };
};
