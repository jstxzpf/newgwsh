import React, { useEffect, useRef, useState } from 'react';
import './EditorA4Paper.css';

interface EditorA4PaperProps {
  children: React.ReactNode;
}

/**
 * A4 拟物化引擎画板包裹器
 * 核心铁律：物理尺寸锁定 794px，动态 Transform 缩放适配视口
 */
export const EditorA4Paper: React.FC<EditorA4PaperProps> = ({ children }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const updateScale = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        // 计算缩放比：(容器宽度 - 留白) / A4宽度
        // 180 是内减的容器 padding 和滚动条安全宽度 (依据前端 UI 设计方案 §四.1)
        const targetScale = containerWidth / (794 + 180);
        // 设定最小缩放系数为 0.5
        setScale(Math.max(0.5, targetScale));
      }
    };

    const resizeObserver = new ResizeObserver(updateScale);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    updateScale();

    return () => resizeObserver.disconnect();
  }, []);

  return (
    <div className="a4-scroll-container" ref={containerRef}>
      <div 
        className="a4-scaling-wrapper" 
        style={{ transform: `scale(${scale})`, transformOrigin: 'top center' }}
      >
        <div className="a4-paper">
          {children}
        </div>
        {scale === 0.5 && (
          <div className="scale-warning">
            视口过小，请切换横屏或大屏设备以获得最佳体验
          </div>
        )}
      </div>
    </div>
  );
};