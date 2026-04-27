import axios from 'axios';
import { useAuthStore } from '../store/useAuthStore';
import { appConfig } from '../config';

const apiClient = axios.create({
  baseURL: appConfig.apiBaseURL,
  timeout: appConfig.axiosTimeout,
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
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        // 修正点：使用 apiClient 内部路径进行刷新
        const res = await apiClient.post('/auth/refresh', null, {
          withCredentials: true 
        });
        const newToken = res.data.access_token;
        useAuthStore.getState().setToken(newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        useAuthStore.getState().logout();
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
