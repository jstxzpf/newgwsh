// Web Worker for Lock Heartbeat
// This worker ensures the heartbeat interval is not throttled by the browser when the tab is inactive.

let intervalId: number | null = null;
let currentIntervalMs = 90000; // Default 90s

self.onmessage = (e: MessageEvent) => {
  const { type, payload } = e.data;

  if (type === 'START') {
    if (intervalId) clearInterval(intervalId);
    
    currentIntervalMs = payload.intervalMs || 90000;
    
    intervalId = self.setInterval(() => {
      self.postMessage({ type: 'TICK' });
    }, currentIntervalMs) as unknown as number;
    
  } else if (type === 'UPDATE_INTERVAL') {
    if (intervalId) clearInterval(intervalId);
    
    currentIntervalMs = payload.intervalMs;
    
    intervalId = self.setInterval(() => {
      self.postMessage({ type: 'TICK' });
    }, currentIntervalMs) as unknown as number;
    
  } else if (type === 'STOP') {
    if (intervalId) clearInterval(intervalId);
    intervalId = null;
  }
};
