import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout, Menu } from 'antd';
import { taixingTheme } from './theme/themeConfig';
import { AntiLeakWatermark } from './components/Security/AntiLeakWatermark';
import { Workspace } from './pages/Workspace';
import { KnowledgeBase } from './pages/KnowledgeBase';
import { Dashboard } from './pages/Dashboard';
import { useAuthStore } from './store/useAuthStore';
import './styles/global.css';

const { Sider } = Layout;

function App() {
  const userInfo = useAuthStore(state => state.userInfo);

  return (
    <ConfigProvider theme={taixingTheme}>
      {userInfo && <AntiLeakWatermark username={userInfo.username} department={userInfo.deptName} />}
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          <Sider width={240} style={{ background: '#003366' }}>
            <div style={{ height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              泰兴统计局 V3.0
            </div>
            <Menu theme="dark" mode="vertical" defaultSelectedKeys={['dashboard']} style={{ background: '#003366', border: 'none', marginTop: '16px' }}>
              <Menu.Item key="dashboard"><Link to="/dashboard">个人工作台</Link></Menu.Item>
              <Menu.Item key="workspace"><Link to="/">公文管理中心</Link></Menu.Item>
              <Menu.Item key="kb"><Link to="/knowledge">统计知识资产库</Link></Menu.Item>
            </Menu>
          </Sider>
          <Layout>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/workspace/:doc_id" element={<Workspace />} />
              <Route path="/knowledge" element={<KnowledgeBase />} />
            </Routes>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
