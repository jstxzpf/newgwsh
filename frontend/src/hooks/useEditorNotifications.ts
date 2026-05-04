import { useEffect, useRef } from 'react';
import { apiClient } from '../api/client';
import { useEditorStore } from '../stores/editorStore';
import { Modal, message } from 'antd';

export function useEditorNotifications() {
  const token = useAuthStore(state => state.token);
  const setReadOnly = useEditorStore(state => state.setReadOnly);
  const connectionRef = useRef<{ es: EventSource | null; retryCount: number; timer?: number }>({ es: null, retryCount: 0 });

  const connect = async () => {
    if (connectionRef.current.es) return;

    try {
      // 申请个人通知票据 (IRON RULE)
      const ticketRes = await apiClient.post('/sse/ticket', { task_id: 'user_events' });
      const ticket = ticketRes.data.data.ticket;

      const es = new EventSource(`/api/v1/sse/user-events?ticket=${ticket}`);
      connectionRef.current.es = es;

      es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        // 处理通知逻辑
        if (data.type === 'notification.rejected') {
          notification.warning({ message: '审批驳回', description: data.rejection_reason });
        } else if (data.type === 'notification.approved') {
          notification.success({ message: '审批通过', description: '公文已批准通过' });
        } else if (data.type === 'notification.lock_reclaimed') {
          Modal.error({ 
            title: '权限收回', 
            content: `您的编辑权限已被收回: ${data.reason}`,
            onOk: () => setReadOnly(true, 'CONFLICT')
          });
          setReadOnly(true, 'CONFLICT');
        }
        connectionRef.current.retryCount = 0;
      };

      es.onerror = () => {
        // IRON RULE: 立即关闭，阻断原生重连
        es.close();
        connectionRef.current.es = null;

        // 受控重连
        if (connectionRef.current.retryCount < 5) {
          connectionRef.current.retryCount++;
          const delay = Math.min(30000, Math.pow(2, connectionRef.current.retryCount) * 2000);
          console.warn(`User SSE disconnected. Retrying in ${delay}ms...`);
          connectionRef.current.timer = window.setTimeout(connect, delay);
        } else {
          message.error('实时通知连接失败，请刷新页面');
        }
      };
    } catch (err) {
      console.error("Failed to fetch User SSE ticket", err);
    }
  };

  useEffect(() => {
    if (token) {
      connect();
    } else {
      if (connectionRef.current.es) connectionRef.current.es.close();
      if (connectionRef.current.timer) clearTimeout(connectionRef.current.timer);
    }

    return () => {
      if (connectionRef.current.es) connectionRef.current.es.close();
      if (connectionRef.current.timer) clearTimeout(connectionRef.current.timer);
    };
  }, [token]);
}

import { useAuthStore } from '../stores/authStore';
import { notification } from 'antd';