import { useEffect, useRef } from 'react';
import apiClient from '../api/client';
import { useEditorStore } from '../store/useEditorStore';
import { LockState } from './useLockGuard';
import { message } from 'antd';

async function sha256(message: string): Promise<string> {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export const useAutoSave = (docId: string | null, lockState: LockState, lockToken: string | null) => {
  const { content, aiPolishedContent, viewMode, lastSavedHash, setLastSavedHash } = useEditorStore();
  
  // 使用 ref 避免闭包陷阱捕获旧状态
  const stateRef = useRef({ content, aiPolishedContent, viewMode, lastSavedHash });
  useEffect(() => {
    stateRef.current = { content, aiPolishedContent, viewMode, lastSavedHash };
  }, [content, aiPolishedContent, viewMode, lastSavedHash]);

  useEffect(() => {
    if (!docId || lockState !== 'LOCKED' || !lockToken) return;

    const performSave = async () => {
      const { content, aiPolishedContent, viewMode, lastSavedHash } = stateRef.current;
      
      // 1. 防空保护：如果根本没有内容，不执行无效保存
      if (!content && !aiPolishedContent) return;
      
      // 2. 本地脏检查：使用 SHA-256 指纹
      const contentToHash = viewMode === 'DIFF' 
        ? (aiPolishedContent || '') 
        : (content || '');
      
      const currentFingerprint = await sha256(`${contentToHash}-${viewMode}`);
      if (currentFingerprint === lastSavedHash) return;

      const payload: any = {};
      if (viewMode === 'DIFF') {
        // DIFF 模式下，仅保存草稿建议稿 aiPolishedContent
        payload.draft_content = aiPolishedContent || '';
      } else {
        payload.content = content || '';
      }

      try {
        await apiClient.post(`/documents/${docId}/auto-save`, payload, {
          params: { lock_token: lockToken }
        });
        // 3. 更新最近保存签章
        useEditorStore.getState().setLastSavedHash(currentFingerprint);
        console.log(`[AutoSave] Synced to cloud at ${new Date().toLocaleTimeString()}`);
      } catch (error: any) {
        console.error('[AutoSave] Blocked or failed:', error);
        message.error('自动保存失败，请检查网络并尝试手动保存');
      }
    };

    // 自动保存频率从配置中心读取
    const timer = setInterval(performSave, appConfig.autoSaveInterval);
    return () => clearInterval(timer);
  }, [docId, lockState, lockToken]);
};

