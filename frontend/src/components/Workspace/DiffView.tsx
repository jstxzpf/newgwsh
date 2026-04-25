import React from 'react';
import { useEditorStore } from '../../store/useEditorStore';
import './A4Engine.css';

export const DiffView: React.FC = () => {
  const { content, aiPolishedContent, setPolishedContent } = useEditorStore();

  return (
    <div style={{ display: 'flex', width: '100%', height: '100%' }}>
      {/* 左栏：原稿，灰色底，只读 */}
      <div style={{ flex: 1, borderRight: '1px solid #ccc', backgroundColor: '#fafafa', padding: '40px', overflowY: 'auto' }}>
        <div className="gov-text" style={{ fontSize: '21.3px', lineHeight: '28pt', color: '#666', whiteSpace: 'pre-wrap' }}>
          <div style={{ marginBottom: '20px', fontWeight: 'bold', color: '#003366' }}>【原始底稿】 (只读)</div>
          {content}
        </div>
      </div>

      {/* 右栏：建议稿，可编辑 */}
      <div style={{ flex: 1, padding: '40px', backgroundColor: '#fff', overflowY: 'auto' }}>
        <div style={{ marginBottom: '20px', fontWeight: 'bold', color: '#52c41a' }}>【AI 润色建议】 (可继续修改)</div>
        <textarea
          className="gov-text"
          value={aiPolishedContent || ''}
          onChange={(e) => setPolishedContent(e.target.value)}
          style={{ 
            width: '100%', 
            height: 'calc(100% - 60px)', 
            border: 'none', 
            resize: 'none', 
            outline: 'none', 
            backgroundColor: 'transparent',
            fontSize: '21.3px', 
            lineHeight: '28pt' 
          }}
        />
      </div>
    </div>
  );
};
