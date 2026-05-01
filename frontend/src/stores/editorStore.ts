import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface EditorState {
  currentDocId: string | null;
  docTypeId: number | null;
  exemplarId: number | null;
  content: string;
  aiPolishedContent: string | null;
  viewMode: 'SINGLE' | 'DIFF';
  context_kb_ids: number[];
  context_snapshot_version: number;
  lock_ttl_remaining: number;
  isBusy: boolean;
  
  // Actions
  setDoc: (docId: string, docTypeId: number) => void;
  setContent: (content: string) => void;
  setAiPolishedContent: (content: string | null) => void;
  setViewMode: (mode: 'SINGLE' | 'DIFF') => void;
  setExemplar: (id: number | null) => void;
  toggleKbNode: (id: number) => void;
  setSnapshotVersion: (version: number) => void;
  updateLockTtl: (ttl: number) => void;
  setBusy: (busy: boolean) => void;
}

export const useEditorStore = create<EditorState>()(
  persist(
    (set) => ({
      currentDocId: null,
      docTypeId: null,
      exemplarId: null,
      content: '',
      aiPolishedContent: null,
      viewMode: 'SINGLE',
      context_kb_ids: [],
      context_snapshot_version: 0,
      lock_ttl_remaining: 0,
      isBusy: false,

      setDoc: (currentDocId, docTypeId) => set({ currentDocId, docTypeId }),
      setContent: (content) => set({ content }),
      setAiPolishedContent: (aiPolishedContent) => set({ aiPolishedContent }),
      setViewMode: (viewMode) => set({ viewMode }),
      setExemplar: (exemplarId) => set({ exemplarId }),
      toggleKbNode: (id) => set((state) => ({
        context_kb_ids: state.context_kb_ids.includes(id)
          ? state.context_kb_ids.filter((kb_id) => kb_id !== id)
          : [...state.context_kb_ids, id],
      })),
      setSnapshotVersion: (context_snapshot_version) => set({ context_snapshot_version }),
      updateLockTtl: (lock_ttl_remaining) => set({ lock_ttl_remaining }),
      setBusy: (isBusy) => set({ isBusy }),
    }),
    {
      name: 'taixing-editor-storage',
      partialize: (state) => ({ viewMode: state.viewMode }), // Only persist viewMode as per spec
    }
  )
);
