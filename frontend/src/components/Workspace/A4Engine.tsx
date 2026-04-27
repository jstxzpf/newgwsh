import React, { useEffect, useRef, useState } from 'react';
import './A4Engine.css';
import { appConfig } from '../../config';

interface A4EngineProps {
  children: React.ReactNode;
}

export const A4Engine: React.FC<A4EngineProps> = ({ children }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const calculateScale = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        // 794 (A4) + 安全边距从配置中心读取
        let newScale = containerWidth / (794 + appConfig.a4Engine.safetyMargin);
        // 最小缩放防畸变
        if (newScale < appConfig.a4Engine.scaleMin) newScale = appConfig.a4Engine.scaleMin;
        // 最大缩放限制
        if (newScale > appConfig.a4Engine.scaleMax) newScale = appConfig.a4Engine.scaleMax;
        setScale(newScale);
      }
    };

    calculateScale();
    window.addEventListener('resize', calculateScale);
    return () => window.removeEventListener('resize', calculateScale);
  }, []);

  return (
    <div 
      ref={containerRef} 
      style={{ 
        width: '100%', 
        height: '100%', 
        overflowY: 'auto', 
        overflowX: scale === 0.5 ? 'auto' : 'hidden',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
        paddingTop: '40px',
        paddingBottom: '40px'
      }}
    >
      <div 
        className="a4-paper gov-text"
        style={{
          transform: `scale(${scale})`,
          transformOrigin: 'top center'
        }}
      >
        {children}
      </div>
    </div>
  );
};
