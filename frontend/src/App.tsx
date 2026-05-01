import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { TAIXING_TOKENS } from './styles/theme';
import './styles/global.css';
import MainLayout from './components/layout/MainLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import DocumentList from './pages/DocumentList';
import Workspace from './pages/Workspace';
import KnowledgeBase from './pages/KnowledgeBase';
import Chat from './pages/Chat';
import Tasks from './pages/Tasks';
import Approvals from './pages/Approvals';
import Settings from './pages/Settings';
import { useAuthStore } from './stores/authStore';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAuthStore();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <ConfigProvider theme={TAIXING_TOKENS}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="documents" element={<DocumentList />} />
            <Route path="workspace/:doc_id" element={<Workspace />} />
            <Route path="knowledge" element={<KnowledgeBase />} />
            <Route path="chat" element={<Chat />} />
            <Route path="tasks" element={<Tasks />} />
            <Route path="approvals" element={<Approvals />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
