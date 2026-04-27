import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { ConfigProvider, Layout, Menu, Badge, Avatar } from 'antd';
import { 
  DashboardOutlined, 
  FormOutlined, 
  DatabaseOutlined, 
  CheckCircleOutlined, 
  SettingOutlined,
  BellOutlined,
  UserOutlined
} from '@ant-design/icons';
import { taixingTheme } from './theme/themeConfig';
import { AntiLeakWatermark } from './components/Security/AntiLeakWatermark';
import { Workspace } from './pages/Workspace';
import { KnowledgeBase } from './pages/KnowledgeBase';
import { Dashboard } from './pages/Dashboard';
import { Approvals } from './pages/Approvals';
import { Settings } from './pages/Settings';
import { Documents } from './pages/Documents';
import { useAuthStore } from './store/useAuthStore';
import { GlobalTaskWatcher } from './components/GlobalTaskWatcher';
import apiClient from './api/client';
import './styles/global.css';

import { Login } from './pages/Login';
import { ProtectedRoute } from './components/Auth/ProtectedRoute';

import { appConfig } from './config';

const { Header, Sider, Content, Footer } = Layout;

const GlobalLayout = () => {
  const userInfo = useAuthStore(state => state.userInfo);
  const location = useLocation();
  const [sysStatus, setSysStatus] = useState<boolean>(true);
  
  const isWorkspace = location.pathname.startsWith('/workspace');
  
  useEffect(() => {
    const probe = async () => {
      try {
        const res = await apiClient.get('/sys/status');
        setSysStatus(res.data.ai_engine_online);
      } catch (e) {
        setSysStatus(false);
      }
    };
    probe();
    // 使用配置定义的探针间隔
    const t = setInterval(probe, appConfig.sysProbeInterval);
    return () => clearInterval(t);
  }, []);

  return (
    <Layout style={{ minHeight: '100vh' }} aria-label="全站主布局容器">
      <Sider width={240} style={{ background: '#003366' }}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <img src="/vite.svg" alt="logo" style={{ width: 24, height: 24, marginRight: 8 }}/>
          泰兴统计局 V3.0
        </div>
        <Menu 
            theme="dark" 
            mode="vertical" 
            selectedKeys={[location.pathname.split('/')[1] || 'dashboard']} 
            style={{ background: '#003366', border: 'none', marginTop: '16px' }}
        >
          <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
            <Link to="/dashboard">个人工作台</Link>
          </Menu.Item>
          <Menu.Item key="documents" icon={<FormOutlined />}>
            <Link to="/documents">公文管理中心</Link>
          </Menu.Item>
          <Menu.Item key="knowledge" icon={<DatabaseOutlined />}>
            <Link to="/knowledge">统计知识资产库</Link>
          </Menu.Item>
          <Menu.Item key="approvals" icon={<CheckCircleOutlined />}>
            <Link to="/approvals">签批管控台</Link>
          </Menu.Item>
          <Menu.Item key="settings" icon={<SettingOutlined />}>
            <Link to="/settings">系统中枢设置</Link>
          </Menu.Item>
        </Menu>
      </Sider>
      
      <Layout>
        <Header style={{ background: '#ffffff', height: '64px', borderBottom: '1px solid #f0f0f0', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontWeight: 'bold', color: '#003366', fontSize: '16px' }}>
            泰兴市国家统计局系统
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <Badge count={2} size="small" offset={[2, 0]}>
              <BellOutlined style={{ fontSize: '18px', color: '#555', cursor: 'pointer' }} />
            </Badge>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '12px' }}>
              <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1677ff' }} />
              <span style={{ fontSize: '14px', color: '#333' }}>{userInfo?.username} ({userInfo?.deptName || '业务科室'})</span>
            </div>
          </div>
        </Header>
        
        <Content style={{ position: 'relative', overflow: 'hidden' }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/workspace/:doc_id" element={<Workspace />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/knowledge" element={<KnowledgeBase />} />
            <Route path="/approvals" element={<Approvals />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
        
        <Footer style={{ height: '24px', background: '#333', color: '#ccc', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', lineHeight: '24px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            探针状态: {sysStatus ? <span style={{color: '#52c41a'}}>🟢 在线 (gemma4:e4b)</span> : <span style={{color: '#ff4d4f'}}>🔴 离线</span>}
          </span>
          <span>
            {isWorkspace ? <span id="global-word-count" style={{marginRight: '16px', color: '#fff'}}>0 纯字数</span> : null}
            泰兴市国家统计局版权所有 © 2026
          </span>
        </Footer>
      </Layout>
    </Layout>
  );
};

function App() {
  const userInfo = useAuthStore(state => state.userInfo);

  return (
    <ConfigProvider theme={taixingTheme}>
      <GlobalTaskWatcher />
      {userInfo && <AntiLeakWatermark username={userInfo.username} department={userInfo.deptName} />}
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={
            <ProtectedRoute>
              <GlobalLayout />
            </ProtectedRoute>
          } />
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;
