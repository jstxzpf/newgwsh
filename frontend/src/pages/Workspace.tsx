import React, { useEffect } from 'react';
import { Button, Spin, Modal, message, Popconfirm } from 'antd';
import { A4Engine } from '../components/Workspace/A4Engine';
import { DiffView } from '../components/Workspace/DiffView';
import { VirtualDocTree } from '../components/Workspace/VirtualDocTree';
import { ChatPanel } from '../components/Workspace/ChatPanel';
import { useEditorStore } from '../store/useEditorStore';
import { useLockGuard } from '../hooks/useLockGuard';
import { useAutoSave } from '../hooks/useAutoSave';
import { LockConflictBanner } from '../components/Workspace/LockConflictBanner';
import { useTaskWatcher } from '../hooks/useTaskWatcher';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';
import { countPureText } from '../utils/wordCount';

export const Workspace: React.FC = () => {
  const { currentDocId, content, aiPolishedContent, setContent, setDocId, viewMode, setViewMode, setPolishedContent, context_kb_ids } = useEditorStore();
  const userInfo = useAuthStore(state => state.userInfo);
  const { lockState } = useLockGuard(currentDocId);
  useAutoSave(currentDocId, lockState);
  
  const { watchTask, taskStatus, progress } = useTaskWatcher();
  const isReadOnly = lockState !== 'LOCKED';
  const isProcessing = taskStatus === 'QUEUED' || taskStatus === 'PROCESSING';
  const wordCount = countPureText(content);

  useEffect(() => {
    if (!currentDocId) {
      setDocId('test-doc-uuid-1234');
    }
  }, [currentDocId, setDocId]);

  const handleTriggerPolish = async () => {
    if (isReadOnly || !currentDocId || !userInfo) return;
    try {
      const res = await apiClient.post(`/documents/${currentDocId}/polish`, {
        context_kb_ids: context_kb_ids
      }, {
        params: { user_id: userInfo.userId }
      });
      watchTask(res.data.task_id, (result) => {
        setPolishedContent(result);
        setViewMode('DIFF');
        message.success('AI 润色完成，已进入比对模式');
      });
    } catch (err) {
      message.error('触发润色失败');
    }
  };

  const handleApplyPolish = async () => {
    if (!currentDocId) return;
    try {
      await apiClient.post(`/documents/${currentDocId}/apply-polish`, {
        final_content: aiPolishedContent
      });
      setContent(aiPolishedContent || '');
      setViewMode('SINGLE');
      setPolishedContent(null);
      message.success('已接受润色并合并原稿');
    } catch (err) {
      message.error('应用润色失败');
    }
  };

  const handleDiscardPolish = async () => {
    if (!currentDocId) return;
    try {
      await apiClient.post(`/documents/${currentDocId}/discard-polish`);
      setViewMode('SINGLE');
      setPolishedContent(null);
      message.info('已丢弃润色建议');
    } catch (err) {
      message.error('操作失败');
    }
  };

  const handleSubmitApproval = async () => {
      try {
          await apiClient.post(`/documents/${currentDocId}/submit`);
          message.success('公文已提交审批');
      } catch (err) {
          message.error('提交失败');
      }
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ height: '56px', background: '#003366', color: '#fff', display: 'flex', alignItems: 'center', padding: '0 24px', gap: '16px' }}>
        <span style={{ fontWeight: 'bold' }}>泰兴市国家统计局公文处理系统</span>
        <div style={{ flex: 1 }}></div>
        
        <Button onClick={() => message.info('快照回滚功能规划中')}>历史快照 ⏱</Button>

        {viewMode === 'SINGLE' && (
          <>
            <Button 
                type="primary" 
                style={{ backgroundColor: '#722ed1', border: 'none' }} 
                onClick={handleTriggerPolish}
                loading={isProcessing}
                disabled={isReadOnly || content.length === 0}
            >
                {isProcessing ? `AI 研读中... ${progress}%` : '✨ AI 智能润色'}
            </Button>
            
            <Popconfirm 
                title="确认提交审批？" 
                description="提交后公文将锁定，只有负责人驳回后才能再次编辑。"
                onConfirm={handleSubmitApproval}
                disabled={isReadOnly || content.length === 0}
            >
                <Button type="primary" style={{ backgroundColor: '#faad14', border: 'none' }} disabled={isReadOnly || content.length === 0}>
                    提交审批
                </Button>
            </Popconfirm>
          </>
        )}
        
        {viewMode === 'DIFF' && (
          <>
            <Popconfirm title="放弃建议？" description="此操作将丢失当前的 AI 润色成果。" onConfirm={handleDiscardPolish}>
                <Button danger>丢弃建议</Button>
            </Popconfirm>
            <Button type="primary" onClick={handleApplyPolish} style={{ backgroundColor: '#52c41a', border: 'none' }}>接受并合并</Button>
          </>
        )}
        
        <span style={{ fontSize: '12px', opacity: 0.8, marginLeft: '16px' }}>
          {lockState === 'ACQUIRING' ? '正在获取锁...' : lockState === 'LOCKED' ? '已锁定' : '只读'}
        </span>
      </div>
      
      <LockConflictBanner lockState={lockState} />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {isProcessing && (
          <div style={{ 
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, 
            backgroundColor: 'rgba(255,255,255,0.7)', backdropFilter: 'blur(2px)', 
            zIndex: 50, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' 
          }}>
            <Spin size="large" />
            <div style={{ marginTop: 20, color: '#003366', fontWeight: 'bold' }}>AI 正在研读台账并组织政务语言，请稍候... ({progress}%)</div>
          </div>
        )}

        <div style={{ width: '280px', borderRight: '1px solid #d9d9d9', background: '#fff', overflow: 'hidden' }}>
          <VirtualDocTree />
        </div>
        <div style={{ flex: 1, background: 'var(--bg-workspace)', overflowY: 'auto' }}>
          {viewMode === 'SINGLE' ? (
            <A4Engine>
              <textarea 
                value={content}
                onChange={(e) => setContent(e.target.value)}
                disabled={isReadOnly}
                style={{ width: '100%', height: '100%', minHeight: '1000px', border: 'none', resize: 'none', outline: 'none', backgroundColor: 'transparent', cursor: isReadOnly ? 'not-allowed' : 'text', color: isReadOnly ? '#555' : 'inherit' }}
                placeholder={isReadOnly ? "只读模式，无法编辑..." : "请在此输入公文正文..."}
                className="gov-text"
              />
            </A4Engine>
          ) : (
            <DiffView />
          )}
        </div>
      </div>

      <div style={{ height: '24px', background: '#f0f2f5', borderTop: '1px solid #d9d9d9', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', fontSize: '12px', color: '#888' }}>
        <span>AI 引擎状态: 🟢 在线</span>
        <span>{wordCount} 纯字数 | 泰兴市国家统计局公文处理系统 V3.0</span>
      </div>
      
      <ChatPanel />
    </div>
  );
};
