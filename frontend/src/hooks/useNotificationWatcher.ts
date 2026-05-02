import { useEffect, useRef } from 'react';
import { useNotificationStore } from '../stores/notificationStore';
import { useAuthStore } from '../stores/authStore';
import { notificationService, taskService } from '../api/services';

export const useNotificationWatcher = () => {
  const { token } = useAuthStore();
  const { setUnreadCount, incrementUnreadCount } = useNotificationStore();
  const esRef = useRef<EventSource | null>(null);

  const fetchUnreadCount = async () => {
    try {
      const res = await notificationService.getUnreadCount();
      setUnreadCount(res.unread_count);
    } catch (err) {
      console.error('Failed to fetch unread count:', err);
    }
  };

  useEffect(() => {
    if (!token) return;

    fetchUnreadCount();

    // Establish personal SSE connection for real-time notifications
    const establishSSE = async () => {
      try {
        // [P0] Security: Request one-time ticket for SSE
        const { ticket } = await taskService.getTicket(''); 
        
        const es = new EventSource(`/api/v1/sse/user-events?ticket=${ticket}`);
        esRef.current = es;

        es.addEventListener('notification.new', () => {
          incrementUnreadCount();
        });

        es.onerror = () => {
          es.close();
        };
      } catch (err) {
        console.error('Failed to establish user SSE:', err);
      }
    };

    establishSSE();

    return () => {
      if (esRef.current) {
        esRef.current.close();
      }
    };
  }, [token]);

  return { refresh: fetchUnreadCount };
};
