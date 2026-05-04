import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { TAIXING_TOKENS } from './styles/theme';
import { MainLayout } from './components/layout/MainLayout';
import { AntiLeakWatermark } from './components/common/AntiLeakWatermark';
import { GlobalTaskWatcher } from './components/common/GlobalTaskWatcher';
import { useEditorNotifications } from './hooks/useEditorNotifications';

// 页面占位组件
const Login = () => <div>Login Page</div>;
const Dashboard = () => <div>Dashboard</div>;
const Workspace = () => <div>Workspace Editor</div>;

export const App: React.FC = () => {
  useEditorNotifications();

  return (
    <ConfigProvider theme={TAIXING_TOKENS}>
      <BrowserRouter>
        <AntiLeakWatermark />
        <GlobalTaskWatcher />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="documents" element={<div>Documents</div>} />
            <Route path="knowledge" element={<div>Knowledge Base</div>} />
            <Route path="approvals" element={<div>Approvals</div>} />
            <Route path="chat" element={<div>Chat</div>} />
            <Route path="settings" element={<div>Settings</div>} />
          </Route>
          {/* Workspace 脱离 Sider 全屏 */}
          <Route path="/workspace/:doc_id" element={<Workspace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};