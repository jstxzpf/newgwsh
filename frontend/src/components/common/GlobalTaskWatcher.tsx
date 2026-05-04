import React, { useEffect, useRef } from 'react';
import { notification } from 'antd';
import { useTaskStore } from '../../stores/taskStore';
import { apiClient } from '../../api/client';

export const GlobalTaskWatcher: React.FC = () => {
  const activeTaskIds = useTaskStore(state => state.activeTaskIds);
  const removeTask = useTaskStore(state => state.removeTask);
  const setTaskResult = useTaskStore(state => state.setTaskResult);
  const connectionsRef = useRef<Record<string, { es: EventSource; retryCount: number; timer?: number }>>({});

  const connect = async (taskId: string) => {
    // 铁律：最大并发连接池限制 (§五.3)
    if (Object.keys(connectionsRef.current).length >= 5) {
      console.warn("SSE pool full, queuing task:", taskId);
      return;
    }
    
    if (connectionsRef.current[taskId]?.es) return;

    try {
      const ticketRes = await apiClient.post('/sse/ticket', { task_id: taskId });
      const ticket = ticketRes.data.data.ticket;

      const es = new EventSource(`/api/v1/sse/${taskId}/events?ticket=${ticket}`);
      const connection = connectionsRef.current[taskId] || { es, retryCount: 0 };
      connection.es = es;
      connectionsRef.current[taskId] = connection;

      es.addEventListener('task.completed', (e: any) => {
        const data = JSON.parse(e.data);
        notification.success({ message: '任务完成', description: `业务处理已成功` });
        setTaskResult(taskId, data);
        cleanup(taskId);
      });

      es.addEventListener('task.failed', (e: any) => {
        const data = JSON.parse(e.data);
        notification.error({ message: '任务失败', description: data.error_message });
        cleanup(taskId);
      });

      es.addEventListener('task.progress', (e: any) => {
        const data = JSON.parse(e.data);
        console.log(`Task ${taskId} progress: ${data.progress_pct}%`);
      });

      es.onerror = () => {
        // 铁律：立即关闭阻断原生重连 (§五.3)
        es.close();
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
    const poll = async () => {
      try {
        const res = await apiClient.get(`/tasks/${taskId}`);
        const data = res.data.data;
        if (data.task_status === 'COMPLETED' || data.task_status === 'FAILED') {
          setTaskResult(taskId, data);
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
      delete connectionsRef.current[taskId];
    }
    removeTask(taskId);
    
    // 释放位置后尝试连接等待中的任务
    const nextTask = activeTaskIds.find(id => !connectionsRef.current[id]);
    if (nextTask) connect(nextTask);
  };

  useEffect(() => {
    activeTaskIds.forEach(taskId => connect(taskId));
  }, [activeTaskIds]);

  return null;
};