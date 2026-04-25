import React from 'react';
import { A4Engine } from '../components/Workspace/A4Engine';
import { useEditorStore } from '../store/useEditorStore';

export const Workspace: React.FC = () => {
  const { content, setContent } = useEditorStore();

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ height: '56px', background: '#003366', color: '#fff', display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <span>泰兴市国家统计局公文处理系统 - 指挥带 (Action Bar)</span>
      </div>
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ width: '280px', borderRight: '1px solid #d9d9d9', background: '#fff' }}>
          VirtualDocTree (挂载台账)
        </div>
        <div style={{ flex: 1, background: 'var(--bg-workspace)' }}>
          <A4Engine>
            <textarea 
              value={content}
              onChange={(e) => setContent(e.target.value)}
              style={{ width: '100%', height: '100%', minHeight: '1000px', border: 'none', resize: 'none', outline: 'none', backgroundColor: 'transparent' }}
              placeholder="请在此输入公文正文..."
              className="gov-text"
            />
          </A4Engine>
        </div>
      </div>
    </div>
  );
};
