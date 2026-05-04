import axios from 'axios';
import { useAuthStore } from '../stores/authStore';
import { message, Modal } from 'antd';

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      if (error.response.status === 401) {
        const errorData = error.response.data;
        if (errorData?.error_code === 'SESSION_KICKED') {
          Modal.warning({
            title: '登录失效',
            content: '您的账号已在其他设备登录，请重新登录',
            onOk: () => useAuthStore.getState().logout()
          });
        } else {
          // 这里可以加入 refresh token 逻辑，暂简化
          useAuthStore.getState().logout();
        }
      } else {
        // 防止前端吞没错误
        message.error(error.response.data?.message || '请求失败');
      }
    }
    return Promise.reject(error);
  }
);