import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { message, Modal } from 'antd';
import { useAuthStore } from '../stores/authStore';

const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { token } = useAuthStore.getState();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data;
    // According to contract, standard response has code and message
    if (res.code && res.code !== 200) {
      message.error(res.message || 'Error');
      return Promise.reject(new Error(res.message || 'Error'));
    }
    return res.data;
  },
  async (error) => {
    const { clearAuth } = useAuthStore.getState();
    
    if (error.response) {
      const { status, data } = error.response;
      
      // Handle 401 Unauthorized
      if (status === 401) {
        if (data?.error_code === 'SESSION_KICKED') {
          Modal.warning({
            title: '下线通知',
            content: '您的账号已在其他设备登录，请重新登录。',
            onOk: () => {
              clearAuth();
              window.location.href = '/login';
            },
          });
        } else {
          // Attempt silent refresh or redirect to login
          clearAuth();
          window.location.href = '/login';
        }
      } 
      // Handle 409 Conflict
      else if (status === 409) {
        message.warning(data?.message || '操作冲突，请刷新后重试');
      }
      // Handle 423 Locked
      else if (status === 423) {
        message.error(data?.message || '文档已被锁定');
      }
      // Handle other errors
      else {
        message.error(data?.message || '系统异常，请稍后再试');
      }
    } else {
      message.error('网络连接异常');
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
