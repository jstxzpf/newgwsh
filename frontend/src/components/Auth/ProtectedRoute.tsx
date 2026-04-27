import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/useAuthStore';

interface Props {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<Props> = ({ children }) => {
  const token = useAuthStore(state => state.token);
  const location = useLocation();

  if (!token) {
    // 重定向到登录页，并记录来源路径
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
