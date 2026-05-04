import React, { useEffect, useRef } from 'react';
import { notification } from 'antd';
import { useTaskStore } from '../../stores/taskStore';
import { apiClient } from '../../api/client';

export const GlobalTaskWatcher: React.FC = () => {
  const activeTaskIds = useTaskStore(state => state.activeTaskIds);
  const removeTask = useTaskStore(state => state.removeTask);
  const setTaskResult = useTaskStore(state => state.setTaskResult);
  const connectionsRef = useRef<Record<string, EventSource>>({});

  useEffect(() => {
    activeTaskIds.forEach(async (taskId) => {
      if (connectionsRef.current[taskId]) return;

      try {
        const ticketRes = await apiClient.post('/sse/ticket', { task_id: taskId });
        const ticket = ticketRes.data.data.ticket;

        const es = new EventSource(`/api/v1/sse/${taskId}/events?ticket=${ticket}`);
        connectionsRef.current[taskId] = es;

        es.addEventListener('task_update', (e: any) => {
          const data = JSON.parse(e.data);
          if (data.task_status === 'COMPLETED') {
            notification.success({ message: '任务完成', description: `任务 ${taskId} 已完成` });
            setTaskResult(taskId, data);
            es.close();
            delete connectionsRef.current[taskId];
            removeTask(taskId);
          } else if (data.task_status === 'FAILED') {
            notification.error({ message: '任务失败', description: data.error_message });
            es.close();
            delete connectionsRef.current[taskId];
            removeTask(taskId);
          }
        });

        es.onerror = () => {
          es.close();
          delete connectionsRef.current[taskId];
          // 降级轮询逻辑略
        };
      } catch (err) {
        console.error("SSE connection failed", err);
      }
    });

    return () => {
      // 卸载时关闭所有连接
    };
  }, [activeTaskIds, removeTask, setTaskResult]);

  return null; // 隐身组件不渲染 DOM
};