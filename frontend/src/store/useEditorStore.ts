import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface EditorState {
  currentDocId: string | null;
  content: string;
  aiPolishedContent: string | null;
  viewMode: 'SINGLE' | 'DIFF';
  lastSavedHash: string;
  
  setDocId: (id: string) => void;
  setContent: (content: string) => void;
  setPolishedContent: (content: string | null) => void;
  setViewMode: (mode: 'SINGLE' | 'DIFF') => void;
  setLastSavedHash: (hash: string) => void;
  clearEditor: () => void;
}

export const useEditorStore = create<EditorState>()(
  persist(
    (set) => ({
      currentDocId: null,
      content: '',
      aiPolishedContent: null,
      viewMode: 'SINGLE',
      lastSavedHash: '',
      
      setDocId: (id) => set({ currentDocId: id }),
      setContent: (content) => set({ content }),
      setPolishedContent: (content) => set({ aiPolishedContent: content }),
      setViewMode: (mode) => set({ viewMode: mode }),
      setLastSavedHash: (hash) => set({ lastSavedHash: hash }),
      clearEditor: () => set({ currentDocId: null, content: '', aiPolishedContent: null, viewMode: 'SINGLE' })
    }),
    {
      name: 'taixing-editor-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        content: state.content, 
        aiPolishedContent: state.aiPolishedContent,
        viewMode: state.viewMode,
        currentDocId: state.currentDocId
      }), // 仅缓存恢复必需字段
    }
  )
);
