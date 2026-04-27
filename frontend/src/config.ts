export const appConfig = {
  apiBaseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  axiosTimeout: Number(import.meta.env.VITE_AXIOS_TIMEOUT) || 10000,
  autoSaveInterval: Number(import.meta.env.VITE_AUTO_SAVE_INTERVAL) || 60000,
  sseMaxRetries: Number(import.meta.env.VITE_SSE_MAX_RETRIES) || 3,
  sseRetryDelayBase: Number(import.meta.env.VITE_SSE_RETRY_DELAY_BASE) || 2000,
  sysProbeInterval: Number(import.meta.env.VITE_SYS_PROBE_INTERVAL) || 60000,
  watermark: {
    rotation: import.meta.env.VITE_WATERMARK_ROTATION || '-20deg',
    opacity: Number(import.meta.env.VITE_WATERMARK_OPACITY) || 0.08,
  },
  a4Engine: {
    scaleMin: Number(import.meta.env.VITE_A4_ENGINE_SCALE_MIN) || 0.5,
    scaleMax: Number(import.meta.env.VITE_A4_ENGINE_SCALE_MAX) || 1.2,
    safetyMargin: Number(import.meta.env.VITE_A4_ENGINE_SAFETY_MARGIN) || 180,
  },
  knowledgePageSize: Number(import.meta.env.VITE_KNOWLEDGE_PAGE_SIZE) || 10,
  virtualTreeMaxWidth: import.meta.env.VITE_VIRTUAL_TREE_MAX_WIDTH || '180px',
};
