import { create } from 'zustand';

interface UserNotification {
  notification_id: number;
  type: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

interface NotificationState {
  unreadCount: number;
  notifications: UserNotification[];
  setUnreadCount: (count: number) => void;
  incrementUnreadCount: () => void;
  setNotifications: (notifications: UserNotification[]) => void;
  markAsRead: (notificationId: number) => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  unreadCount: 0,
  notifications: [],
  setUnreadCount: (count) => set({ unreadCount: count }),
  incrementUnreadCount: () => set((state) => ({ unreadCount: state.unreadCount + 1 })),
  setNotifications: (notifications) => set({ notifications }),
  markAsRead: (notificationId) => set((state) => ({
    unreadCount: Math.max(0, state.unreadCount - 1),
    notifications: state.notifications.map(n => 
      n.notification_id === notificationId ? { ...n, is_read: true } : n
    )
  })),
}));
