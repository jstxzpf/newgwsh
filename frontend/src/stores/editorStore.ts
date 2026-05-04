import { create } from 'zustand'

interface EditorState {
  currentDocId: string | null;
  docTypeId: number | null;
  exemplarId: number | null;
  content: string;
  aiPolishedContent: string | null;
  viewMode: 'SINGLE' | 'DIFF';
  context_kb_ids: number[];
  context_snapshot_version: number;
  isBusy: boolean;
  
  setDocId: (id: string | null) => void;
  setContent: (content: string) => void;
  setPolishedContent: (content: string | null) => void;
  setViewMode: (mode: 'SINGLE' | 'DIFF') => void;
  setBusy: (busy: boolean) => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  currentDocId: null,
  docTypeId: null,
  exemplarId: null,
  content: '',
  aiPolishedContent: null,
  viewMode: 'SINGLE',
  context_kb_ids: [],
  context_snapshot_version: 0,
  isBusy: false,
  
  setDocId: (id) => set({ currentDocId: id }),
  setContent: (content) => set({ content }),
  setPolishedContent: (content) => set({ aiPolishedContent: content }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setBusy: (busy) => set({ isBusy: busy })
}))