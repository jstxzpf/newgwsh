import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { ConfigProvider, Layout, Menu } from 'antd';
import { 
  DashboardOutlined, 
  FormOutlined, 
  DatabaseOutlined, 
  CheckCircleOutlined, 
  SettingOutlined 
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
              <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
                <Link to="/dashboard">个人工作台</Link>
              </Menu.Item>
              <Menu.Item key="docs" icon={<FormOutlined />}>
                <Link to="/documents">公文管理中心</Link>
              </Menu.Item>
              <Menu.Item key="kb" icon={<DatabaseOutlined />}>
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
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/workspace/:doc_id" element={<Workspace />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/knowledge" element={<KnowledgeBase />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
}

export default App;
