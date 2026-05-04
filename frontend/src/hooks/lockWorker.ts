// frontend/src/hooks/lockWorker.ts
let intervalId: number | null = null;

self.onmessage = (e) => {
  const { type, interval } = e.data;
  
  if (type === 'START') {
    if (intervalId) clearInterval(intervalId);
    intervalId = self.setInterval(() => {
      self.postMessage({ type: 'TICK' });
    }, interval);
  } else if (type === 'STOP') {
    if (intervalId) clearInterval(intervalId);
    intervalId = null;
  }
};