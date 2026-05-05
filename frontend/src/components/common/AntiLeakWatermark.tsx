import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../../stores/authStore';

export const AntiLeakWatermark: React.FC = () => {
  const userInfo = useAuthStore(state => state.userInfo);
  const [timeStr, setTimeStr] = useState(new Date().toLocaleString());

  useEffect(() => {
    const timer = setInterval(() => setTimeStr(new Date().toLocaleString()), 60000);
    return () => clearInterval(timer);
  }, []);

  if (!userInfo) return null;

  const watermarkText = `${userInfo.username} ${userInfo.full_name} ${userInfo.department_name || ''} ${timeStr}`;

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
        pointerEvents: 'none', zIndex: 9999, overflow: 'hidden', opacity: 0.08,
        display: 'flex', flexWrap: 'wrap', transform: 'rotate(-20deg)', transformOrigin: 'center'
      }}
    >
      {Array.from({ length: 100 }).map((_, i) => (
        <div key={i} style={{ width: '300px', height: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {watermarkText}
        </div>
      ))}
    </div>
  );
};