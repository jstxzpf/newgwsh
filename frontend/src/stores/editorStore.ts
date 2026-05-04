import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface EditorState {
  currentDocId: string | null;
  docTypeId: number | null;
  docTypeName: string | null;
  status: string | null;
  content: string;
  aiPolishedContent: string | null;
  draftSuggestion: string | null;
  viewMode: 'SINGLE' | 'DIFF';
  isReadOnly: boolean;
  readOnlyReason: 'CONFLICT' | 'IMMUTABLE' | null;
  isBusy: boolean;
  lock_ttl_remaining: number;
  context_kb_ids: number[];
  context_snapshot_version: number;
  exemplarId: number | null;
  
  setDocMetadata: (id: string | null, typeId: number | null, typeName: string | null, status: string | null) => void;
  setContent: (content: string) => void;
  setPolishedResult: (polished: string | null, suggestion: string | null) => void;
  setDraftSuggestion: (suggestion: string | null) => void;
  setViewMode: (mode: 'SINGLE' | 'DIFF') => void;
  setReadOnly: (isReadOnly: boolean, reason?: 'CONFLICT' | 'IMMUTABLE' | null) => void;
  setBusy: (busy: boolean) => void;
  setLockTTL: (ttl: number) => void;
  resetEditor: () => void;
}

export const useEditorStore = create<EditorState>()(
  persist(
    (set) => ({
      currentDocId: null,
      docTypeId: null,
      docTypeName: null,
      status: null,
      content: '',
      aiPolishedContent: null,
      draftSuggestion: null,
      viewMode: 'SINGLE',
      isReadOnly: false,
      readOnlyReason: null,
      isBusy: false,
      lock_ttl_remaining: 0,
      context_kb_ids: [],
      context_snapshot_version: 0,
      exemplarId: null,
      
      setDocMetadata: (id, typeId, typeName, status) => set({ 
        currentDocId: id, 
        docTypeId: typeId, 
        docTypeName: typeName,
        status 
      }),
      setContent: (content) => set({ content }),
      setPolishedResult: (polished, suggestion) => set({ 
        aiPolishedContent: polished, 
        draftSuggestion: suggestion || polished,
        viewMode: polished ? 'DIFF' : 'SINGLE'
      }),
      setDraftSuggestion: (suggestion) => set({ draftSuggestion: suggestion }),
      setViewMode: (mode) => set({ viewMode: mode }),
      setReadOnly: (isReadOnly, reason = null) => set({ isReadOnly, readOnlyReason: reason }),
      setBusy: (busy) => set({ isBusy: busy }),
      setLockTTL: (ttl) => set({ lock_ttl_remaining: ttl }),
      resetEditor: () => set({
        currentDocId: null, docTypeId: null, docTypeName: null, status: null,
        content: '', aiPolishedContent: null, draftSuggestion: null,
        viewMode: 'SINGLE', isReadOnly: false, readOnlyReason: null, isBusy: false,
        lock_ttl_remaining: 0, context_kb_ids: [], context_snapshot_version: 0, exemplarId: null
      })
    }),
    {
      name: 'taixing-editor-storage',
      partialize: (state) => ({ viewMode: state.viewMode }), // 仅持久化 viewMode (对齐 §六.1)
    }
  )
)