import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { TAIXING_TOKENS } from './styles/theme';
import { MainLayout } from './components/layout/MainLayout';
import { AntiLeakWatermark } from './components/common/AntiLeakWatermark';
import { GlobalTaskWatcher } from './components/common/GlobalTaskWatcher';
import { useEditorNotifications } from './hooks/useEditorNotifications';
import { useAuthStore } from './stores/authStore';
import { apiClient } from './api/client';

// 导入真实页面组件
import { Login } from './pages/Login/Login';
import { Dashboard } from './pages/Dashboard/Dashboard';
import { Workspace } from './pages/Workspace/Workspace';
import { Documents } from './pages/Documents/Documents';
import { Knowledge } from './pages/Knowledge/Knowledge';

// 路由守卫组件
const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, userInfo, setUserInfo } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    if (token && !userInfo) {
      // 刷新页面或重新进入时补全信息
      apiClient.get('/auth/me').then(res => setUserInfo(res.data.data)).catch(() => {});
    }
  }, [token, userInfo, setUserInfo]);

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  useEditorNotifications();

  return (
    <ConfigProvider theme={TAIXING_TOKENS}>
      <BrowserRouter>
        <AntiLeakWatermark />
        <GlobalTaskWatcher />
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route path="/" element={
            <AuthGuard>
              <MainLayout />
            </AuthGuard>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="documents" element={<Documents />} />
            <Route path="knowledge" element={<Knowledge />} />
            <Route path="approvals" element={<div>Approvals</div>} />
            <Route path="chat" element={<div>Chat</div>} />
            <Route path="settings" element={<div>Settings</div>} />
          </Route>

          <Route path="/workspace/:doc_id" element={
            <AuthGuard>
              <Workspace />
            </AuthGuard>
          } />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};