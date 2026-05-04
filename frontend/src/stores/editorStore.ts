import { create } from 'zustand'

interface EditorState {
  // 公文基本元数据
  currentDocId: string | null;
  docTypeId: number | null;
  docTypeName: string | null;
  status: string | null;
  
  // 编辑核心内容
  content: string; // SINGLE 模式下的内容，或 DIFF 模式下的左栏原稿
  aiPolishedContent: string | null; // DIFF 模式下的 AI 建议稿（右栏初始值）
  draftSuggestion: string | null; // DIFF 模式下用户对建议稿的二改草稿（右栏当前值）
  
  // 交互状态
  viewMode: 'SINGLE' | 'DIFF';
  isReadOnly: boolean;
  readOnlyReason: 'CONFLICT' | 'IMMUTABLE' | null;
  isBusy: boolean;
  lock_ttl_remaining: number;
  
  // RAG 与范文上下文
  context_kb_ids: number[];
  context_snapshot_version: number;
  exemplarId: number | null;
  
  // Actions
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

export const useEditorStore = create<EditorState>((set) => ({
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
    draftSuggestion: suggestion || polished, // 若云端无二改草稿，则初始化为建议稿
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
}))