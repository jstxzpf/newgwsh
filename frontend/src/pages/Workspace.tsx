import React, { useEffect, useRef, useState } from 'react';
import { Layout, Button, Space, Tag, Divider, Tree, message, Popconfirm, Alert, Skeleton } from 'antd';
import {
  ArrowLeftOutlined,
  ThunderboltOutlined,
  DownloadOutlined,
  HistoryOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useEditorStore } from '../stores/editorStore';
import { useAuthStore } from '../stores/authStore';
import { useLockGuard } from '../hooks/useLockGuard';
import { documentService, taskService } from '../api/services';

const { Sider, Content } = Layout;

const Workspace: React.FC = () => {
  const { doc_id } = useParams<{ doc_id: string }>();
  const navigate = useNavigate();
  const paperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [docStatus, setDocStatus] = useState<string>('DRAFTING');

  const {
    content,
    setContent,
    viewMode,
    setViewMode,
    aiPolishedContent,
    setAiPolishedContent,
    isBusy,
    setBusy,
  } = useEditorStore();
  
  const { token } = useAuthStore();
  const { isReadOnly, readOnlyReason, acquireLock, lockToken } = useLockGuard(doc_id || null);

  // Dynamic Scaling Logic
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        const newScale = containerWidth / (794 + 80); // 794 is A4 width, 80 for padding
        setScale(Math.max(0.5, newScale));
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Fetch initial document details
  useEffect(() => {
    if (doc_id) {
      documentService.getDetail(doc_id)
        .then((res: any) => {
          setContent(res.content || '');
          setDocStatus(res.status);
          
          // Resume DIFF mode if cloud has unapplied AI suggestions
          if (res.ai_polished_content) {
             setAiPolishedContent(res.draft_suggestion || res.ai_polished_content);
             setViewMode('DIFF');
          } else {
             setViewMode('SINGLE');
          }
        })
        .catch(() => message.error('无法加载文档'));
    }
  }, [doc_id]);

  // Auto Save Logic (Every 60s)
  useEffect(() => {
    const autoSaveInterval = setInterval(async () => {
      if (isReadOnly || !doc_id || !lockToken) return;

      try {
        const payload = viewMode === 'SINGLE' 
          ? { content } 
          : { draft_content: aiPolishedContent };
          
        await documentService.autoSave(doc_id, payload);
        console.log('Auto-saved successfully');
      } catch (err) {
        console.error('Auto-save failed', err);
      }
    }, 60000);

    return () => clearInterval(autoSaveInterval);
  }, [content, aiPolishedContent, viewMode, isReadOnly, doc_id, lockToken]);

  // beforeunload Recovery Release
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (doc_id && lockToken && !isReadOnly) {
        // Send fetch keepalive to save and release
        const payload = {
          doc_id,
          lock_token: lockToken,
          content: viewMode === 'SINGLE' ? content : undefined,
          draft_content: viewMode === 'DIFF' ? aiPolishedContent : undefined
        };
        fetch('/api/v1/locks/release', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload),
          keepalive: true
        });
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [doc_id, lockToken, content, aiPolishedContent, isReadOnly, viewMode, token]);

  const handleInputFocus = () => {
    if (!isReadOnly && docStatus === 'DRAFTING') {
      acquireLock();
    }
  };

  const handlePolish = async () => {
    if (!doc_id) return;
    setBusy(true);
    message.loading('AI 正在研读挂载台账，请稍候...');
    try {
      await taskService.startPolish({
         doc_id,
         context_kb_ids: [], // To be wired to Tree
         context_snapshot_version: Date.now(), // Mocking snapshot version
      });
      // The GlobalTaskWatcher will handle the SSE push and UI state update
    } catch (err) {
      message.error('发起润色失败');
      setBusy(false);
    }
  };

  const handleApplyPolish = async () => {
    if (!doc_id) return;
    setBusy(true);
    try {
      await documentService.applyPolish(doc_id, { final_content: aiPolishedContent || '' });
      setContent(aiPolishedContent || '');
      setAiPolishedContent(null);
      setViewMode('SINGLE');
      message.success('已应用建议并保存');
    } catch (err) {
      message.error('应用建议失败');
    } finally {
      setBusy(false);
    }
  };

  const handleDiscardPolish = async () => {
    if (!doc_id) return;
    setBusy(true);
    try {
       await documentService.discardPolish(doc_id);
       setAiPolishedContent(null);
       setViewMode('SINGLE');
       message.info('已丢弃建议');
    } catch (err) {
       message.error('操作失败');
    } finally {
       setBusy(false);
    }
  };

  const handleSubmit = async () => {
    if (!doc_id) return;
    setBusy(true);
    try {
      await documentService.submit(doc_id);
      message.success('已提交审批');
      setDocStatus('SUBMITTED');
      navigate('/documents');
    } catch (err) {
      message.error('提交失败');
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = () => {
    if (doc_id) {
       window.open(documentService.download(doc_id), '_blank');
    }
  };

  return (
    <Layout style={{ height: 'calc(100vh - 64px - 24px)', background: '#f0f2f5' }}>
      {/* Sidebar for KB Tree */}
      <Sider width={280} theme="light" style={{ borderRight: '1px solid #e8e8e8', overflow: 'auto' }}>
        <div style={{ padding: '16px' }}>
          <h3>知识资产挂载</h3>
          <Divider style={{ margin: '12px 0' }} />
          <Tree
            checkable
            selectable={false}
            treeData={[
              { title: '全局库', key: 'base', children: [{ title: '统计法.pdf', key: 'kb-1' }] },
              { title: '科室共享', key: 'dept', children: [{ title: '2024一季度分析.docx', key: 'kb-2' }] },
            ]}
          />
          <Divider />
          <h3>参考范文</h3>
          <div style={{ padding: '8px', border: '1px dashed #ccc', borderRadius: 4, textAlign: 'center', color: '#999' }}>
            未选择范文
          </div>
        </div>
      </Sider>

      <Layout>
        {/* Top Action Bar */}
        <div style={{ background: '#fff', padding: '8px 24px', display: 'flex', flexDirection: 'column', borderBottom: '1px solid #e8e8e8' }}>
          
          {/* Read Only Banner */}
          {isReadOnly && (
             <Alert 
               message={readOnlyReason || '文档当前处于只读模式'} 
               type={docStatus !== 'DRAFTING' ? 'info' : 'warning'} 
               showIcon 
               style={{ marginBottom: 8, width: '100%', justifyContent: 'center' }} 
               banner
             />
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <Space>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')}>返回</Button>
              <Divider type="vertical" />
              <Tag color="blue">调研分析</Tag>
              <span style={{ color: '#999', fontSize: 12 }}>文档ID: {doc_id}</span>
            </Space>

            <Space>
              {viewMode === 'SINGLE' ? (
                <>
                  <Button icon={<HistoryOutlined />}>历史快照</Button>
                  <Button type="primary" style={{ background: '#722ed1' }} icon={<ThunderboltOutlined />} onClick={handlePolish} loading={isBusy} disabled={isReadOnly}>AI 智能润色</Button>
                  {docStatus === 'APPROVED' ? (
                     <Button type="primary" icon={<DownloadOutlined />} onClick={handleDownload}>下载国标文档 📥</Button>
                  ) : (
                     <Button icon={<DownloadOutlined />}>排版预览</Button>
                  )}
                  <Button type="primary" onClick={handleSubmit} loading={isBusy} disabled={isReadOnly || docStatus !== 'DRAFTING'}>提交审批</Button>
                </>
              ) : (
                <Space>
                  <Button type="primary" icon={<CheckOutlined />} onClick={handleApplyPolish} loading={isBusy}>接受并合并</Button>
                  <Popconfirm title="确定丢弃建议吗？" onConfirm={handleDiscardPolish}>
                    <Button icon={<CloseOutlined />} danger loading={isBusy}>丢弃</Button>
                  </Popconfirm>
                </Space>
              )}
            </Space>
          </div>
        </div>

        {/* Paper Container */}
        <Content ref={containerRef} style={{ overflow: 'auto', padding: '40px 0', position: 'relative' }}>
          {/* Skeleton Pacifier (Section V.2) */}
          {isBusy && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              zIndex: 10,
              display: 'flex',
              justifyContent: 'center',
              paddingTop: 40,
              backdropFilter: 'blur(2px)',
              background: 'rgba(240, 242, 245, 0.4)'
            }}>
              <div className="a4-paper" style={{ transform: `scale(${scale})`, transformOrigin: 'top center', padding: '72px 90px' }}>
                <Skeleton active paragraph={{ rows: 20 }} />
                <div style={{ 
                  position: 'absolute', 
                  top: '40%', 
                  left: 0, 
                  width: '100%', 
                  textAlign: 'center',
                  fontWeight: 'bold',
                  color: '#003366',
                  textShadow: '0 2px 4px rgba(255,255,255,0.8)'
                }}>
                  AI 正在研读挂载台账，请稍候...
                </div>
              </div>
            </div>
          )}

          <div
            className="a4-paper document-content"
            ref={paperRef}
            style={{
              transform: `scale(${scale})`,
            }}
          >
            {viewMode === 'SINGLE' ? (
              <textarea
                style={{ width: '100%', height: '100%', border: 'none', outline: 'none', resize: 'none', background: 'transparent' }}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onFocus={handleInputFocus}
                readOnly={isReadOnly}
                placeholder={isReadOnly ? "" : "在此开始起草公文..."}
              />
            ) : (
              <div style={{ display: 'flex', gap: 40, height: '100%' }}>
                <div style={{ flex: 1, padding: 10, background: '#fafafa', borderRadius: 4, cursor: 'not-allowed' }}>
                  <div style={{ color: '#999', marginBottom: 8, fontSize: 12 }}>[只读原稿]</div>
                  {content}
                </div>
                <div style={{ flex: 1, padding: 10, background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 4 }}>
                  <div style={{ color: '#52c41a', marginBottom: 8, fontSize: 12 }}>[AI 建议稿 - 可编辑]</div>
                  <textarea
                    style={{ width: '100%', height: 'calc(100% - 20px)', border: 'none', outline: 'none', resize: 'none', background: 'transparent' }}
                    value={aiPolishedContent || ''}
                    onChange={(e) => setAiPolishedContent(e.target.value)}
                  />
                </div>
              </div>
            )}
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default Workspace;
