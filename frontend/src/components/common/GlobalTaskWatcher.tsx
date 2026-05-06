import React, { useEffect, useRef } from 'react';
import { notification } from 'antd';
import { useTaskStore } from '../../stores/taskStore';
import { apiClient } from '../../api/client';

export const GlobalTaskWatcher: React.FC = () => {
  const activeTaskIds = useTaskStore(state => state.activeTaskIds);
  const removeTask = useTaskStore(state => state.removeTask);
  const setTaskResult = useTaskStore(state => state.setTaskResult);
  const connectionsRef = useRef<Record<string, { es: EventSource; retryCount: number; timer?: number; finished: boolean }>>({});

  const connect = async (taskId: string) => {
    // 铁律：最大并发连接池限制 (§五.3)
    if (Object.keys(connectionsRef.current).length >= 5) {
      return;
    }
    
    if (connectionsRef.current[taskId]?.es || connectionsRef.current[taskId]?.finished) return;

    try {
      const ticketRes = await apiClient.post('/sse/ticket', { task_id: taskId });
      const ticket = ticketRes.data.data.ticket;

      const es = new EventSource(`/api/v1/sse/${taskId}/events?ticket=${ticket}`);
      const connection = connectionsRef.current[taskId] || { es, retryCount: 0, finished: false };
      connection.es = es;
      connection.finished = false;
      connectionsRef.current[taskId] = connection;

      es.addEventListener('task.completed', (e: any) => {
        if (connection.finished) return;
        const data = JSON.parse(e.data);
        notification.success({ message: '任务完成', description: `业务处理已成功` });
        setTaskResult(taskId, data);
        connection.finished = true;
        cleanup(taskId);
      });

      es.addEventListener('task.failed', (e: any) => {
        if (connection.finished) return;
        const data = JSON.parse(e.data);
        notification.error({ message: '任务失败', description: data.error_message });
        setTaskResult(taskId, data);
        connection.finished = true;
        cleanup(taskId);
      });

      es.addEventListener('task.progress', (e: any) => {
        const data = JSON.parse(e.data);
        // 知识库上下文过期告警：对用户可见
        if (data.message && data.message.startsWith('⚠')) {
          notification.warning({ message: '上下文变更提醒', description: data.message, duration: 8 });
        }
      });

      es.onerror = () => {
        es.close();
        if (connection.finished) return;
        
        connection.es = null;
        if (connection.retryCount < 3) {
          connection.retryCount++;
          const delay = Math.pow(2, connection.retryCount) * 1000;
          connection.timer = window.setTimeout(() => connect(taskId), delay);
        } else {
          notification.warning({ message: '连接降级', description: '已切换为轮询模式' });
          startPolling(taskId);
        }
      };
    } catch (err) {
      console.error(`SSE ticket request failed`, err);
    }
  };

  const startPolling = (taskId: string) => {
    const conn = connectionsRef.current[taskId];
    const poll = async () => {
      if (conn?.finished) return;
      try {
        const res = await apiClient.get(`/tasks/${taskId}`);
        const data = res.data.data;
        if (data.task_status === 'COMPLETED' || data.task_status === 'FAILED') {
          setTaskResult(taskId, data);
          if (conn) conn.finished = true;
          cleanup(taskId);
        } else {
          window.setTimeout(poll, 5000);
        }
      } catch (e) {
        window.setTimeout(poll, 10000);
      }
    };
    poll();
  };

  const cleanup = (taskId: string) => {
    const conn = connectionsRef.current[taskId];
    if (conn) {
      if (conn.es) conn.es.close();
      if (conn.timer) clearTimeout(conn.timer);
      // 注意：不立即从 connectionsRef 删除，防止 activeTaskIds 变化导致的重连
    }
    removeTask(taskId);
    
    // 延时清理连接引用
    setTimeout(() => {
      delete connectionsRef.current[taskId];
    }, 5000);
  };

  useEffect(() => {
    activeTaskIds.forEach(taskId => {
      if (!connectionsRef.current[taskId]) {
        connect(taskId);
      }
    });
  }, [activeTaskIds]);

  return null;
};