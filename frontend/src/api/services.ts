import apiClient from './client';

/**
 * 核心响应模型
 */
export interface ListResponse<T> {
  items: T[];
  total: number;
}

/**
 * 公文相关模型
 */
export interface DocumentRecord {
  doc_id: string;
  title: string;
  doc_type: string;
  status: string;
  creator_name: string;
  updated_at: string;
  department_name?: string;
  content?: string;
  ai_polished_content?: string;
  draft_suggestion?: string;
}

export interface DocumentInitParams {
  doc_type_id: number;
  title?: string;
}

/**
 * 知识库相关模型
 */
export interface KBResource {
  key: string;
  name: string;
  type: 'file' | 'folder';
  security: '核心' | '重要' | '一般';
  status: 'READY' | 'PARSING' | 'FAILED';
  owner: string;
  updatedAt: string;
  children?: KBResource[];
}

/**
 * 系统监控相关模型
 */
export interface DashboardStats {
  pending_tasks: number;
  ai_engine_online: boolean;
  document_counts: {
    DRAFTING: number;
    SUBMITTED: number;
    APPROVED: number;
  };
}

export interface SystemStatus {
  db_online: boolean;
  redis_online: boolean;
  ai_online: boolean;
  cpu_usage: number;
}

/**
 * 认证服务
 */
export const authService = {
  login: (data: any) => {
    const params = new URLSearchParams();
    params.append('username', data.username);
    params.append('password', data.password);
    return apiClient.post<any, any>('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  },
  me: () => apiClient.get<any, any>('/auth/me'),
  logout: () => apiClient.post<any, void>('/auth/logout'),
};

/**
 * 公文服务
 */
export const documentService = {
  getList: (params: any) => 
    apiClient.get<any, ListResponse<DocumentRecord>>('/documents/', { params }),
    
  init: (data: DocumentInitParams) => 
    apiClient.post<any, DocumentRecord>('/documents/init', data),
    
  getDetail: (docId: string) => 
    apiClient.get<any, DocumentRecord>(`/documents/${docId}`),
    
  delete: (docId: string) => 
    apiClient.delete<any, void>(`/documents/${docId}`),
    
  autoSave: (docId: string, data: { content?: string; draft_content?: string }) => 
    apiClient.post<any, void>(`/documents/${docId}/auto-save`, data),
    
  submit: (docId: string) => 
    apiClient.post<any, void>(`/documents/${docId}/submit`),
    
  revise: (docId: string) => 
    apiClient.post<any, void>(`/documents/${docId}/revise`),
    
  applyPolish: (docId: string, data: { final_content: string }) => 
    apiClient.post<any, void>(`/documents/${docId}/apply-polish`, data),
    
  discardPolish: (docId: string) => 
    apiClient.post<any, void>(`/documents/${docId}/discard-polish`),
    
  getSnapshots: (docId: string, params: any) => 
    apiClient.get<any, ListResponse<any>>(`/documents/${docId}/snapshots`, { params }),
    
  download: (docId: string) => `/api/v1/documents/${docId}/download`,
};

/**
 * 锁服务
 */
export const lockService = {
  acquire: (data: { doc_id: string }) => 
    apiClient.post<any, { lock_token: string; ttl: number }>('/locks/acquire', data),
    
  heartbeat: (data: { doc_id: string; lock_token: string }) => 
    apiClient.post<any, { ttl: number }>('/locks/heartbeat', data),
    
  release: (data: { doc_id: string; lock_token: string; content?: string; draft_content?: string }) => 
    apiClient.post<any, void>('/locks/release', data),
    
  getConfig: () => 
    apiClient.get<any, { ttl: number; heartbeat_interval: number }>('/locks/config'),
};

/**
 * 异步任务服务
 */
export const taskService = {
  startPolish: (data: { doc_id: string; lock_token: string; context_kb_ids: number[]; context_snapshot_version: number }) => 
    apiClient.post<any, { task_id: string }>('/tasks/polish', data),
    
  startFormat: (data: { doc_id: string }) => 
    apiClient.post<any, { task_id: string }>('/tasks/format', data),
    
  getStatus: (taskId: string) => 
    apiClient.get<any, { status: string; progress: number; result?: any }>('/tasks/${taskId}'),
    
  getTicket: (taskId: string) => 
    apiClient.post<any, { ticket: string }>('/sse/ticket', { task_id: taskId }),
};

/**
 * 知识库服务
 */
export const kbService = {
  getHierarchy: () => 
    apiClient.get<any, KBResource[]>('/kb/hierarchy'),
    
  getSnapshotVersion: () => 
    apiClient.get<any, { version: number }>('/kb/snapshot-version'),
    
  upload: (formData: FormData) => 
    apiClient.post<any, void>('/kb/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    
  delete: (kbId: number) => 
    apiClient.delete<any, void>(`/kb/${kbId}`),
};

/**
 * 通知服务
 */
export const notificationService = {
  getList: (params: any) => 
    apiClient.get<any, ListResponse<any>>('/notifications/', { params }),
    
  getUnreadCount: () => 
    apiClient.get<any, { unread_count: number }>('/notifications/unread-count'),
    
  markAsRead: (notificationId: number) => 
    apiClient.post<any, void>(`/notifications/${notificationId}/read`),
    
  markAllAsRead: () => 
    apiClient.post<any, void>('/notifications/read-all'),
};

/**
 * 系统服务
 */
export const sysService = {
  getStats: () => 
    apiClient.get<any, DashboardStats>('/sys/dashboard-stats'),
    
  getStatus: () => 
    apiClient.get<any, SystemStatus>('/sys/status'),
    
  getConfig: () => 
    apiClient.get<any, any>('/sys/config'),
};
