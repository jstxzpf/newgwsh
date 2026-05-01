import React, { useState } from 'react';
import { Layout, Menu, Button, Avatar, Dropdown, Badge, Drawer } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  MessageOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  BellOutlined,
  LogoutOutlined,
  UserOutlined,
  MenuUnfoldOutlined,
  MenuFoldOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';
import AntiLeakWatermark from '../common/AntiLeakWatermark';
import GlobalTaskWatcher from '../common/GlobalTaskWatcher';

const { Header, Sider, Content, Footer } = Layout;

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const { userInfo, clearAuth } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    clearAuth();
    navigate('/login');
  };

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '个人工作台' },
    { key: '/documents', icon: <FileTextOutlined />, label: '公文中心' },
    { key: '/knowledge', icon: <DatabaseOutlined />, label: '知识库' },
    { key: '/chat', icon: <MessageOutlined />, label: '智能助手' },
    { key: '/tasks', icon: <CheckCircleOutlined />, label: '任务中心' },
    { key: '/approvals', icon: <CheckCircleOutlined />, label: '签批管控台' },
    { key: '/settings', icon: <SettingOutlined />, label: '系统中枢' },
  ];

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: '个人信息' },
      { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
    ],
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AntiLeakWatermark />
      <GlobalTaskWatcher />
      <Sider trigger={null} collapsible collapsed={collapsed} width={240}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 18, fontWeight: 'bold' }}>
          {collapsed ? 'TX' : '泰兴调查队公文'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: '0 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', boxShadow: '0 1px 4px rgba(0,21,41,.08)' }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px', width: 64, height: 64 }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <Badge count={5} size="small">
              <Button type="text" icon={<BellOutlined />} onClick={() => setNotificationOpen(true)} />
            </Badge>
            <Dropdown menu={userMenu}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <Avatar icon={<UserOutlined />} />
                <span>{userInfo?.full_name} ({userInfo?.department_name})</span>
              </div>
            </Dropdown>
          </div>
        </Header>
        <Content style={{ margin: '0', overflow: 'initial' }}>
          <Outlet />
        </Content>
        <Footer style={{ textAlign: 'center', padding: '4px 0', height: 24, fontSize: 12, background: '#333', color: '#ccc' }}>
          国家统计局泰兴调查队公文处理系统 V3.0 ©2026 | AI 引擎: 🟢 在线 | 字数: 0
        </Footer>
      </Layout>

      <Drawer
        title="通知中心"
        placement="right"
        onClose={() => setNotificationOpen(false)}
        open={notificationOpen}
      >
        <p>暂无新通知</p>
      </Drawer>
    </Layout>
  );
};

export default MainLayout;
