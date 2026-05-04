import React, { useEffect, useState } from 'react';
import { Layout, Menu, Space, Badge, Divider, Typography } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { useEditorStore } from '../../stores/editorStore';
import { apiClient } from '../../api/client';
import { countWords } from '../../utils/wordCount';
import { TAIXING_BRAND } from '../../styles/theme';

const { Header, Sider, Content, Footer } = Layout;
const { Text } = Typography;

export const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const userInfo = useAuthStore(state => state.userInfo);
  const content = useEditorStore(state => state.content);
  const [aiStatus, setAiStatus] = useState<'online' | 'offline'>('offline');

  useEffect(() => {
    // 全局探针 (§三.1)
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
    const timer = setInterval(checkStatus, 30000);
    return () => clearInterval(timer);
  }, []);

  const wordCount = countWords(content);
  const isWorkspace = location.pathname.includes('/workspace');

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <img src="/logo.png" alt="logo" style={{ height: '32px', marginRight: '12px' }} />
          <div style={{ fontWeight: 'bold', fontSize: '18px', color: TAIXING_BRAND.primaryColor }}>{TAIXING_BRAND.fullName}</div>
        </div>
        <Space size="large">
           <Badge count={0} dot offset={[-2, 0]}>
             <span style={{ fontSize: '18px', cursor: 'pointer' }}>🔔</span>
           </Badge>
           <span style={{ fontWeight: 500 }}>{userInfo?.full_name} ({userInfo?.department_name})</span>
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