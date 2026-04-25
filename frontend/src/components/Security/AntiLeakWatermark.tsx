import React, { useEffect, useState } from 'react';

interface WatermarkProps {
  username: string;
  department: string;
}

export const AntiLeakWatermark: React.FC<WatermarkProps> = ({ username, department }) => {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const update = () => setTimeStr(new Date().toISOString().slice(0, 19).replace('T', ' '));
    update();
    const timer = setInterval(update, 60000);
    return () => clearInterval(timer);
  }, []);

  const watermarkText = `${department} - ${username} - ${timeStr}`;

  return (
    <div 
      style={{
        position: 'fixed',
        top: 0, left: 0, width: '100vw', height: '100vh',
        pointerEvents: 'none',
        zIndex: 9999,
        overflow: 'hidden',
        opacity: 0.08,
        display: 'flex',
        flexWrap: 'wrap',
        transform: 'rotate(-20deg) scale(1.5)',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '100px'
      }}
    >
      {Array.from({ length: 150 }).map((_, i) => (
        <div key={i} style={{ fontSize: '14px', color: '#000', whiteSpace: 'nowrap' }}>
          {watermarkText}
        </div>
      ))}
    </div>
  );
};
