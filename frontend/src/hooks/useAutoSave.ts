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
      
      // 1. 防空保护：如果根本没有内容，不执行无效保存
      if (!state.content && !state.aiPolishedContent) return;
      
      // 2. 本地脏检查：如果与上次保存的指纹相同则跳过 (修复点)
      const currentFingerprint = `${state.content.length}-${state.viewMode}-${state.aiPolishedContent?.length || 0}`;
      if (currentFingerprint === state.lastSavedHash) return;

      const payload: any = {};
      if (state.viewMode === 'DIFF') {
        payload.draft_content = state.content;
      } else {
        payload.content = state.content;
      }

      try {
        await apiClient.post(`/documents/${docId}/auto-save`, payload);
        // 3. 更新最近保存签章 (修复点)
        useEditorStore.getState().setLastSavedHash(currentFingerprint);
        console.log(`[AutoSave] Synced to cloud at ${new Date().toLocaleTimeString()}`);
      } catch (error) {
        console.error('[AutoSave] Blocked or failed:', error);
      }
    };

    // 每 60 秒自动保存
    const timer = setInterval(performSave, 60000);
    return () => clearInterval(timer);
  }, [docId, lockState]);
};
