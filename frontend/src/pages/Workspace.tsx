import React, { useEffect, useState } from 'react';
import { Button, Modal, message, Popconfirm, Skeleton } from 'antd';
import { A4Engine } from '../components/Workspace/A4Engine';
import { DiffView } from '../components/Workspace/DiffView';
import { VirtualDocTree } from '../components/Workspace/VirtualDocTree';
import { ChatPanel } from '../components/Workspace/ChatPanel';
import { SnapshotRecoveryDrawer } from '../components/Workspace/SnapshotRecoveryDrawer';
import { useEditorStore } from '../store/useEditorStore';
import { useLockGuard } from '../hooks/useLockGuard';
import { useAutoSave } from '../hooks/useAutoSave';
import { LockConflictBanner } from '../components/Workspace/LockConflictBanner';
import { useTaskWatcher } from '../hooks/useTaskWatcher';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';
import { countPureText } from '../utils/wordCount';
import { appConfig } from '../config';

export const Workspace: React.FC = () => {
  const { currentDocId, content, aiPolishedContent, setContent, setDocId, viewMode, setViewMode, setPolishedContent, context_kb_ids } = useEditorStore();
  const userInfo = useAuthStore(state => state.userInfo);
  const { lockState, lockToken } = useLockGuard(currentDocId);
  useAutoSave(currentDocId, lockState, lockToken);
  
  const [docStatus, setDocStatus] = useState<string>('DRAFTING');
  const [initialLoading, setInitialLoading] = useState(true); // 【对齐修复】消除漫游恢复闪烁
  const { watchTask, taskStatus, progress } = useTaskWatcher();
  
  const isConflict = lockState === 'READONLY_CONFLICT';
  const isImmutable = docStatus !== 'DRAFTING';
  const isReadOnly = isConflict || isImmutable;
  
  const wordCount = countPureText(content);
  const isProcessing = taskStatus === 'QUEUED' || taskStatus === 'PROCESSING';

  // 颗粒度对齐：更新全局 Footer 中的字数
  useEffect(() => {
    const el = document.getElementById('global-word-count');
    if (el) el.innerText = `${wordCount} 纯字数`;
  }, [wordCount]);

  useEffect(() => {
    if (currentDocId) {
        setInitialLoading(true);
        apiClient.get(`/documents/${currentDocId}`).then(res => {
            if (res.data) {
                const doc = res.data;
                setDocStatus(doc.status);
                
                // 漫游状态恢复逻辑 (对齐基准：原子化更新防止闪烁)
                const newContent = doc.content || '';
                let newPolishedContent = null;
                let newViewMode: 'SINGLE' | 'DIFF' = 'SINGLE';

                if (doc.ai_polished_content) {
                    newPolishedContent = doc.draft_suggestion || doc.ai_polished_content;
                    newViewMode = 'DIFF';
                }

                setContent(newContent);
                setPolishedContent(newPolishedContent);
                setViewMode(newViewMode);
            }
        }).catch(() => {
            message.error('获取公文详情失败，请检查网络或权限');
        }).finally(() => {
            setInitialLoading(false);
        });
    }
  }, [currentDocId]);

  const handleTriggerPolish = async () => {
    if (isReadOnly || !currentDocId || !userInfo || !lockToken) return;
    try {
      const res = await apiClient.post(`/documents/${currentDocId}/polish`, {
        context_kb_ids: context_kb_ids
      }, {
        params: { lock_token: lockToken } // 移除外部 user_id，由后端从 Token 提取
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
    if (!currentDocId || !lockToken) return;
    try {
      await apiClient.post(`/documents/${currentDocId}/apply-polish`, {
        final_content: aiPolishedContent
      }, {
        params: { lock_token: lockToken }
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
      // 【级联修复】丢弃润色时清理可能存在的持久化脏数据
      localStorage.removeItem('taixing-editor-storage'); 
      message.info('已丢弃润色建议并清理本地缓存');
    } catch (err) {
      message.error('操作失败');
    }
  };

  const handleFormatAndDownload = async () => {
    if (!currentDocId) return;
    try {
      // 1. 触发排版任务
      const res = await apiClient.post(`/documents/${currentDocId}/format`);
      message.info('排版任务已派发，正在生成国标文档...');
      
      // 2. 使用 watchTask 监听
      watchTask(res.data.task_id, () => {
        const downloadUrl = `${appConfig.apiBaseURL}/documents/${currentDocId}/download`;
        window.open(downloadUrl, '_blank');
        message.success('文档已生成，正在启动下载');
      });
    } catch (e) {
      message.error('触发排版失败');
    }
  };

  const handleSubmitApproval = async () => {
      try {
          await apiClient.post(`/documents/${currentDocId}/submit`);
          message.success('公文已提交审批');
          setDocStatus('SUBMITTED');
      } catch (err) {
          message.error('提交失败');
      }
  };

  if (initialLoading) {
    return (
      <div style={{ padding: 24 }}>
        <Skeleton active paragraph={{ rows: 10 }} />
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 次级指挥带 (蓝色) */}
      <div style={{ height: '48px', background: '#003366', color: '#fff', display: 'flex', alignItems: 'center', padding: '0 24px', gap: '16px' }}>
        <SnapshotRecoveryDrawer docId={currentDocId} />

        <div style={{ flex: 1 }}></div>

        {viewMode === 'SINGLE' ? (
          <>
            <Button 
                type="primary" 
                style={{ background: 'linear-gradient(135deg, #722ed1, #faad14)', border: 'none' }} 
                onClick={handleTriggerPolish}
                loading={isProcessing}
                disabled={isReadOnly || content.length === 0}
            >
                {isProcessing ? `AI 研读中... ${progress}%` : '✨ AI 智能润色'}
            </Button>

            <Button 
                style={{ backgroundColor: '#08979c', color: '#fff', border: 'none' }} 
                onClick={handleFormatAndDownload}
                disabled={isReadOnly || content.length === 0}
            >
                GB国标排版并下载
            </Button>
            
            <Popconfirm 
                title="确认提交审批？" 
                onConfirm={handleSubmitApproval}
                disabled={isReadOnly || content.length === 0}
            >
                <Button type="primary" style={{ backgroundColor: '#faad14', border: 'none' }} disabled={isReadOnly || content.length === 0}>
                    提交审批
                </Button>
            </Popconfirm>
          </>
        ) : (
          <>
            <Popconfirm title="放弃建议？" onConfirm={handleDiscardPolish}>
                <Button danger>丢弃建议</Button>
            </Popconfirm>
            <Button type="primary" onClick={handleApplyPolish} style={{ backgroundColor: '#52c41a', border: 'none' }}>接受并合并</Button>
          </>
        )}

        <span style={{ fontSize: '12px', opacity: 0.8, marginLeft: '16px' }}>
          {isConflict ? '锁冲突 (只读)' : isImmutable ? '已归档 (只读)' : '已锁定编辑'}
        </span>
      </div>
      
      <LockConflictBanner lockState={lockState} isImmutable={isImmutable} />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {isProcessing && (
          <div style={{ 
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, 
            backgroundColor: 'rgba(255,255,255,0.7)', backdropFilter: 'blur(2px)', 
            zIndex: 50, display: 'flex', flexDirection: 'column', padding: '100px 150px' 
          }}>
            <h3 style={{ color: '#003366', textAlign: 'center', marginBottom: 40 }}>
              AI 正在研读挂载台账，请稍候... ({progress}%)
            </h3>
            <Skeleton active paragraph={{ rows: 15 }} />
          </div>
        )}

        <div style={{ width: '280px', borderRight: '1px solid #d9d9d9', background: '#fff', overflow: 'hidden' }}>
          <VirtualDocTree />
        </div>
        <div style={{ flex: 1, background: 'var(--bg-workspace)', overflowY: 'auto' }}>
          {viewMode === 'SINGLE' ? (
            <A4Engine>
              <textarea 
                value={content || ''}
                onChange={(e) => {
                  if (!isReadOnly) setContent(e.target.value);
                }}
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
      
      <ChatPanel />
    </div>
  );
};
