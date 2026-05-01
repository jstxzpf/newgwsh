import apiClient from './client';

export interface BaseResponse<T> {
  code: number;
  message: string;
  data: T;
}

export const authService = {
  login: (data: any) => apiClient.post<any, any>('/auth/login', data),
  me: () => apiClient.get<any, any>('/auth/me'),
  logout: () => apiClient.post<any, any>('/auth/logout'),
};

export const documentService = {
  getList: (params: any) => apiClient.get<any, any>('/documents', { params }),
  init: (data: { doc_type_id: number; title?: string }) => apiClient.post<any, any>('/documents/init', data),
  getDetail: (docId: string) => apiClient.get<any, any>(`/documents/${docId}`),
  delete: (docId: string) => apiClient.delete<any, any>(`/documents/${docId}`),
  autoSave: (docId: string, data: any) => apiClient.post<any, any>(`/documents/${docId}/auto-save`, data),
  submit: (docId: string) => apiClient.post<any, any>(`/documents/${docId}/submit`),
  revise: (docId: string) => apiClient.post<any, any>(`/documents/${docId}/revise`),
  applyPolish: (docId: string, data: { final_content: string }) => apiClient.post<any, any>(`/documents/${docId}/apply-polish`, data),
  discardPolish: (docId: string) => apiClient.post<any, any>(`/documents/${docId}/discard-polish`),
  getSnapshots: (docId: string, params: any) => apiClient.get<any, any>(`/documents/${docId}/snapshots`, { params }),
  download: (docId: string) => `/api/v1/documents/${docId}/download`,
};

export const lockService = {
  acquire: (data: { doc_id: string }) => apiClient.post<any, any>('/locks/acquire', data),
  heartbeat: (data: { doc_id: string; lock_token: string }) => apiClient.post<any, any>('/locks/heartbeat', data),
  release: (data: { doc_id: string; lock_token: string; content?: string }) => apiClient.post<any, any>('/locks/release', data),
  getConfig: () => apiClient.get<any, any>('/locks/config'),
};

export const taskService = {
  startPolish: (data: any) => apiClient.post<any, any>('/tasks/polish', data),
  startFormat: (data: { doc_id: string }) => apiClient.post<any, any>('/tasks/format', data),
  getStatus: (taskId: string) => apiClient.get<any, any>(`/tasks/${taskId}`),
  getTicket: (taskId: string) => apiClient.post<{ ticket: string }, { ticket: string }>('/sse/ticket', { task_id: taskId }),
};

export const kbService = {
  getHierarchy: () => apiClient.get<any, any>('/kb/hierarchy'),
  getSnapshotVersion: () => apiClient.get<any, any>('/kb/snapshot-version'),
  upload: (formData: FormData) => apiClient.post<any, any>('/kb/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  delete: (kbId: number) => apiClient.delete<any, any>(`/kb/${kbId}`),
};
