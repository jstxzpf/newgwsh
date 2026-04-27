import React, { useEffect, useState } from 'react';
import { appConfig } from '../../config';

interface WatermarkProps {
  username: string;
  department: string;
}

export const AntiLeakWatermark: React.FC<WatermarkProps> = ({ username, department }) => {
  const now = new Date();
  const dateStr = now.toISOString().slice(0, 10);
  const watermarkText = `${department} - ${username} - ${dateStr}`;

  return (
    <div 
      style={{
        position: 'fixed',
        top: 0, left: 0, width: '100vw', height: '100vh',
        pointerEvents: 'none',
        zIndex: 9999,
        overflow: 'hidden',
        opacity: appConfig.watermark.opacity,
        display: 'flex',
        flexWrap: 'wrap',
        transform: `rotate(${appConfig.watermark.rotation}) scale(1.5)`,
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
