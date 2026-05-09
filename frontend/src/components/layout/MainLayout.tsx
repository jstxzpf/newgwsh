import React, { useEffect, useState, useCallback } from 'react';
import { Layout, Menu, Space, Badge, Divider, Typography, Popover, List, Button, Dropdown } from 'antd';
import {
  BellOutlined,
  UserOutlined,
  SwapOutlined,
  LogoutOutlined,
  CheckOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { useEditorStore } from '../../stores/editorStore';
import { apiClient } from '../../api/client';
import { countWords } from '../../utils/wordCount';
import { TAIXING_BRAND } from '../../styles/theme';

const { Header, Sider, Content, Footer } = Layout;

const NOTIFICATION_TYPE_ICON: Record<string, React.ReactNode> = {
  TASK_COMPLETED: <CheckOutlined style={{ color: '#52c41a' }} />,
  TASK_FAILED: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
  DOC_APPROVED: <CheckOutlined style={{ color: '#52c41a' }} />,
  DOC_REJECTED: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
  LOCK_RECLAIMED: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
};

export const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const userInfo = useAuthStore(state => state.userInfo);
  const logout = useAuthStore(state => state.logout);
  const content = useEditorStore(state => state.content);
  const [aiStatus, setAiStatus] = useState<'online' | 'offline'>('offline');
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [notifLoading, setNotifLoading] = useState(false);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await apiClient.get('/notifications/unread-count');
      setUnreadCount(res.data.data?.unread_count ?? 0);
    } catch { /* ignore */ }
  }, []);

  const fetchNotifications = useCallback(async () => {
    setNotifLoading(true);
    try {
      const res = await apiClient.get('/notifications', { params: { page: 1, page_size: 10 } });
      setNotifications(res.data.data?.items ?? []);
    } catch { /* ignore */ } finally {
      setNotifLoading(false);
    }
  }, []);

  const handleMarkRead = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiClient.post(`/notifications/${id}/read`);
      setNotifications(prev => prev.map(n => n.notification_id === id ? { ...n, is_read: true } : n));
      fetchUnreadCount();
    } catch { /* ignore */ }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient.post('/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await apiClient.get('/sys/status');
        if (res.data.data.ai_engine_online) setAiStatus('online');
        else setAiStatus('offline');
      } catch {
        setAiStatus('offline');
      }
    };
    checkStatus();
    fetchUnreadCount();
    const timer = setInterval(() => { checkStatus(); fetchUnreadCount(); }, 30000);
    return () => clearInterval(timer);
  }, [fetchUnreadCount]);

  const wordCount = countWords(content);
  const isWorkspace = location.pathname.includes('/workspace');

  const notificationPopover = (
    <div style={{ width: 360, maxHeight: 480 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Typography.Text strong>消息通知</Typography.Text>
        {unreadCount > 0 && (
          <Button type="link" size="small" onClick={handleMarkAllRead}>全部已读</Button>
        )}
      </div>
      {notifications.length === 0 ? (
        <Typography.Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>
          暂无通知
        </Typography.Text>
      ) : (
        <List
          loading={notifLoading}
          style={{ maxHeight: 360, overflow: 'auto' }}
          dataSource={notifications}
          renderItem={(item: any) => (
            <List.Item
              style={{
                cursor: item.doc_id ? 'pointer' : 'default',
                background: item.is_read ? undefined : '#e6f4ff',
                padding: '8px 12px',
              }}
              onClick={() => { if (item.doc_id) navigate(`/workspace/${item.doc_id}`); }}
              actions={item.is_read ? undefined : [
                <Button key="read" type="link" size="small" onClick={(e) => handleMarkRead(item.notification_id, e)}>已读</Button>
              ]}
            >
              <List.Item.Meta
                avatar={NOTIFICATION_TYPE_ICON[item.type] || <BellOutlined />}
                title={item.content}
                description={item.created_at ? new Date(item.created_at).toLocaleString() : ''}
              />
            </List.Item>
          )}
        />
      )}
    </div>
  );

  const userMenuItems = {
    items: [
      {
        key: 'info',
        label: (
          <div style={{ padding: '4px 0' }}>
            <div style={{ fontWeight: 600 }}>{userInfo?.full_name}</div>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{userInfo?.department_name}</Typography.Text>
          </div>
        ),
        disabled: true,
      },
      { type: 'divider' as const },
      {
        key: 'switch',
        label: '切换账号',
        icon: <SwapOutlined />,
        onClick: () => {
          logout();
          navigate('/login');
        },
      },
      {
        key: 'logout',
        label: '退出登录',
        icon: <LogoutOutlined />,
        danger: true,
        onClick: () => {
          logout();
        },
      },
    ],
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <img src="/logo.png" alt="logo" style={{ height: '32px', marginRight: '12px' }} />
          <div style={{ fontWeight: 'bold', fontSize: '18px', color: TAIXING_BRAND.primaryColor }}>{TAIXING_BRAND.fullName}</div>
        </div>
        <Space size="large">
          <Popover
            content={notificationPopover}
            title={null}
            trigger="click"
            placement="bottomRight"
            onOpenChange={(visible) => { if (visible) fetchNotifications(); }}
          >
            <Badge count={unreadCount} offset={[-2, 0]} size="small">
              <BellOutlined style={{ fontSize: 20, cursor: 'pointer', color: '#555' }} />
            </Badge>
          </Popover>
          <Dropdown menu={userMenuItems} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <UserOutlined style={{ fontSize: 16 }} />
              <span style={{ fontWeight: 500 }}>{userInfo?.full_name}</span>
            </Space>
          </Dropdown>
        </Space>
      </Header>
      <Layout>
        <Sider width={240} style={{ background: TAIXING_BRAND.primaryColor }} collapsible>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname.split('/')[1] || 'dashboard']}
            style={{ background: 'transparent', borderRight: 0 }}
            items={[
              { key: 'dashboard', label: '个人工作台', onClick: () => navigate('/dashboard') },
              { key: 'documents', label: '公文管理中心', onClick: () => navigate('/documents') },
              { key: 'knowledge', label: '统计知识资产', onClick: () => navigate('/knowledge') },
              { key: 'approvals', label: '科长签批管控', onClick: () => navigate('/approvals'), disabled: (userInfo?.role_level || 0) < 5 },
              { key: 'chat', label: '智能穿透问答', onClick: () => navigate('/chat') },
              { key: 'settings', label: '系统中枢设置', onClick: () => navigate('/settings'), disabled: (userInfo?.role_level || 0) < 99 },
            ]}
          />
        </Sider>
        <Layout>
          <Content style={{ background: TAIXING_BRAND.bgColor, margin: 0, minHeight: 280, position: 'relative' }}>
            <Outlet />
          </Content>
          <Footer style={{ 
            height: '24px', padding: '0 16px', 
            background: '#333', color: '#fff', fontSize: '12px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center'
          }}>
            <div style={{ display: 'flex', alignItems: 'center' }}>
               <Badge status={aiStatus === 'online' ? 'success' : 'error'} />
               <span style={{ marginLeft: 6, color: '#aaa' }}>AI 探针: {aiStatus === 'online' ? '在线' : '离线'}</span>
            </div>
            <div style={{ color: '#888' }}>
               © 2026 {TAIXING_BRAND.name} | 极致匠心 V3.0
            </div>
            <div>
               {isWorkspace && (
                 <Space split={<Divider type="vertical" style={{ borderColor: '#666' }} />}>
                   <span style={{ color: '#aaa' }}>A4 物理排版</span>
                   <span style={{ color: TAIXING_BRAND.accentColor, fontWeight: 'bold' }}>正文计数: {wordCount}</span>
                 </Space>
               )}
            </div>
          </Footer>
        </Layout>
      </Layout>
    </Layout>
  );
};