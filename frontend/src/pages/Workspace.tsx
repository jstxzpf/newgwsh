import React, { useEffect } from 'react';
import { A4Engine } from '../components/Workspace/A4Engine';
import { useEditorStore } from '../store/useEditorStore';
import { useLockGuard } from '../hooks/useLockGuard';
import { useAutoSave } from '../hooks/useAutoSave';
import { LockConflictBanner } from '../components/Workspace/LockConflictBanner';

export const Workspace: React.FC = () => {
  const { currentDocId, content, setContent, setDocId } = useEditorStore();

  // 模拟进入页面时初始化一个 docId (实际应从路由参数获取)
  useEffect(() => {
    if (!currentDocId) {
      setDocId('test-doc-uuid-1234');
    }
  }, [currentDocId, setDocId]);

  // 挂载锁守卫
  const { lockState } = useLockGuard(currentDocId);
  // 挂载自动保存引擎
  useAutoSave(currentDocId, lockState);

  const isReadOnly = lockState !== 'LOCKED';

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ height: '56px', background: '#003366', color: '#fff', display: 'flex', alignItems: 'center', padding: '0 24px' }}>
        <span>泰兴市国家统计局公文处理系统 - 指挥带 (Action Bar)</span>
        <span style={{ marginLeft: 'auto', fontSize: '12px', opacity: 0.8 }}>
          {lockState === 'ACQUIRING' ? '正在获取锁...' : lockState === 'LOCKED' ? '已锁定' : '只读'}
        </span>
      </div>
      
      <LockConflictBanner lockState={lockState} />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ width: '280px', borderRight: '1px solid #d9d9d9', background: '#fff' }}>
          VirtualDocTree (挂载台账)
        </div>
        <div style={{ flex: 1, background: 'var(--bg-workspace)' }}>
          <A4Engine>
            <textarea 
              value={content}
              onChange={(e) => setContent(e.target.value)}
              disabled={isReadOnly}
              style={{ 
                width: '100%', 
                height: '100%', 
                minHeight: '1000px', 
                border: 'none', 
                resize: 'none', 
                outline: 'none', 
                backgroundColor: 'transparent',
                cursor: isReadOnly ? 'not-allowed' : 'text',
                color: isReadOnly ? '#555' : 'inherit'
              }}
              placeholder={isReadOnly ? "只读模式，无法编辑..." : "请在此输入公文正文..."}
              className="gov-text"
            />
          </A4Engine>
        </div>
      </div>
    </div>
  );
};
