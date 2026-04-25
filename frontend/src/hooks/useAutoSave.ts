import { useEffect, useRef } from 'react';
import apiClient from '../api/client';
import { useEditorStore } from '../store/useEditorStore';
import { LockState } from './useLockGuard';

export const useAutoSave = (docId: string | null, lockState: LockState) => {
  const { content, aiPolishedContent, viewMode, lastSavedHash, setLastSavedHash } = useEditorStore();
  
  // 使用 ref 避免闭包陷阱捕获旧状态
  const stateRef = useRef({ content, aiPolishedContent, viewMode, lastSavedHash });
  useEffect(() => {
    stateRef.current = { content, aiPolishedContent, viewMode, lastSavedHash };
  }, [content, aiPolishedContent, viewMode, lastSavedHash]);

  useEffect(() => {
    if (!docId || lockState !== 'LOCKED') return;

    const performSave = async () => {
      const state = stateRef.current;
      
      // 简单的本地脏检查模拟
      if (state.content.length === 0 && !state.aiPolishedContent) return; 

      const payload: any = {};
      if (state.viewMode === 'DIFF') {
        payload.draft_content = state.content;
      } else {
        payload.content = state.content;
      }

      try {
        await apiClient.post(`/documents/${docId}/auto-save`, payload);
        console.log(`[AutoSave] Success at ${new Date().toLocaleTimeString()}`);
      } catch (error) {
        console.error('[AutoSave] Failed:', error);
      }
    };

    // 每 60 秒自动保存
    const timer = setInterval(performSave, 60000);
    return () => clearInterval(timer);
  }, [docId, lockState]);
};
