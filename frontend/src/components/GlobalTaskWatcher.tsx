import React, { useEffect, useRef } from 'react';
import { message, notification } from 'antd';
import { useTaskStore } from '../store/useTaskStore';
import { useAuthStore } from '../store/useAuthStore';
import apiClient from '../api/client';

export const GlobalTaskWatcher: React.FC = () => {
  const { activeTasks, updateTask, removeTask } = useTaskStore();
  const userInfo = useAuthStore(state => state.userInfo);
  const connections = useRef<Record<string, EventSource>>({});

  useEffect(() => {
    if (!userInfo) return;

    const taskIds = Object.keys(activeTasks);
    
    // 1. Cleanup completed/failed or manually removed tasks
    Object.keys(connections.current).forEach(id => {
      if (!taskIds.includes(id)) {
        connections.current[id].close();
        delete connections.current[id];
      }
    });

    // 2. Establish new connections (Pool limit <= 5)
    taskIds.forEach(async (id) => {
      if (!connections.current[id]) {
        if (Object.keys(connections.current).length >= 5) {
          message.warning('任务并发池已满(5/5)，请等待其他任务完成。');
          return;
        }

        try {
          // Get SSE Ticket (15s TTL)
          const res = await apiClient.post('/sse/ticket', null, {
            params: { task_id: id, user_id: userInfo.userId }
          });
          
          const es = new EventSource(`/api/v1/sse/${id}/events?ticket=${res.data.ticket}`);
          connections.current[id] = es;

          es.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateTask(id, { progress: data.progress, status: data.status, result: data.result });
            
            if (data.status === 'COMPLETED' || data.status === 'FAILED') {
              es.close();
              delete connections.current[id];
              
              if (data.status === 'COMPLETED') {
                notification.success({ 
                  message: '任务完成', 
                  description: `任务 ${id.slice(0, 8)} 已成功执行。` 
                });
              } else {
                notification.error({ 
                  message: '任务失败', 
                  description: `后台处理引擎返回异常，请检查审计日志。` 
                });
              }
              // Keep task in state for 5s to allow UI feedback
              setTimeout(() => removeTask(id), 5000);
            }
          };

          es.onerror = () => {
            es.close();
            delete connections.current[id];
            updateTask(id, { status: 'FAILED' });
            notification.error({ message: 'SSE 断开', description: '与服务器的任务推流链接意外中断。' });
          };
        } catch (e) {
          console.error("Failed to mount SSE for", id);
        }
      }
    });
  }, [activeTasks, userInfo, updateTask, removeTask]);

  return null;
};
