import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';
import { appConfig } from '../config';

/**
 * 统一锁管理中心
 * 提供标准化的申请、续期与释放逻辑，确保前后端契约一致。
 */
export const lockManager = {
  /**
   * 申请编辑锁
   */
  async acquire(docId: string): Promise<string> {
    const res = await apiClient.post(`/locks/acquire`, null, {
      params: { doc_id: docId }
    });
    return res.data.lock_token;
  },

  /**
   * 释放编辑锁 (支持 keepalive 用于卸载清理)
   */
  async release(docId: string, token: string, useBeacon = false) {
    if (useBeacon) {
      const authHeader = `Bearer ${useAuthStore.getState().token || ''}`;
      return fetch(`${appConfig.apiBaseURL}/locks/release?doc_id=${docId}&lock_token=${token}`, {
        method: 'POST',
        keepalive: true,
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json'
        }
      }).catch(() => {});
    }
    return apiClient.post(`/locks/release`, null, {
      params: { doc_id: docId, lock_token: token }
    });
  },

  /**
   * 发送心跳续期
   */
  async heartbeat(docId: string, token: string) {
    return apiClient.post(`/locks/heartbeat`, null, {
      params: { doc_id: docId, lock_token: token }
    });
  }
};
