import React from 'react';
import { Layout, Menu } from 'antd';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

const { Header, Sider, Content, Footer } = Layout;

export const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const userInfo = useAuthStore(state => state.userInfo);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontWeight: 'bold', fontSize: '18px' }}>泰兴调查队公文处理系统</div>
        <div>
          {userInfo?.full_name} ({userInfo?.username})
        </div>
      </Header>
      <Layout>
        <Sider width={240} style={{ background: '#003366' }}>
          <Menu
            theme="dark"
            mode="inline"
            defaultSelectedKeys={['dashboard']}
            style={{ background: 'transparent' }}
            items={[
              { key: 'dashboard', label: '工作台', onClick: () => navigate('/dashboard') },
              { key: 'documents', label: '公文中心', onClick: () => navigate('/documents') },
              { key: 'knowledge', label: '知识库', onClick: () => navigate('/knowledge') },
              { key: 'approvals', label: '审批管控', onClick: () => navigate('/approvals') },
              { key: 'chat', label: '智能问答', onClick: () => navigate('/chat') },
              { key: 'settings', label: '系统中枢', onClick: () => navigate('/settings') },
            ]}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content style={{ background: '#f0f2f5', margin: 0, minHeight: 280 }}>
            <Outlet />
          </Content>
          <Footer style={{ textAlign: 'center', height: '24px', padding: '0' }}>
            系统探针: 在线 | Copyright © 2026
          </Footer>
        </Layout>
      </Layout>
    </Layout>
  );
};