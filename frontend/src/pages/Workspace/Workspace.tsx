import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Spin, message, Button, Space, Tag, Popconfirm, Modal } from 'antd';
import { LeftOutlined, SendOutlined, BulbOutlined, DownloadOutlined, HistoryOutlined } from '@ant-design/icons';
import { useEditorStore } from '../../stores/editorStore';
import { useTaskStore } from '../../stores/taskStore';
import { useLockGuard } from '../../hooks/useLockGuard';
import { apiClient } from '../../api/client';
import { EditorA4Paper } from '../../components/common/EditorA4Paper/EditorA4Paper';
import { VirtualDocTree } from './components/VirtualDocTree';
import { ExemplarPanel } from './components/ExemplarPanel';
import { SnapshotRecoveryDrawer } from './components/SnapshotRecoveryDrawer';
import './Workspace.css';

const { Header, Content, Sider } = Layout;

export const Workspace: React.FC = () => {
  const { doc_id } = useParams<{ doc_id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [snapshotDrawerOpen, setSnapshotDrawerOpen] = useState(false);
  const [scale, setScale] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  const addTask = useTaskStore(state => state.addTask);
  const taskResults = useTaskStore(state => state.taskResults);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const polishTimeoutRef = useRef<number | null>(null);

  // A4 视口自适应算法 (Task 1)
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const parentWidth = containerRef.current.clientWidth - 48; // 减去 padding
        const paperWidth = 794; // A4 标准宽度
        if (parentWidth < paperWidth) {
          setScale(parentWidth / paperWidth);
        } else {
          setScale(1);
        }
      }
    };
    
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, [loading]);

  const { 
    content, setContent, viewMode, setViewMode, 
    isReadOnly, readOnlyReason, setReadOnly,
    docTypeName, setDocMetadata, aiPolishedContent,
    draftSuggestion, setPolishedResult, setDraftSuggestion,
    isBusy, setBusy, resetEditor, exemplarId, context_kb_ids
  } = useEditorStore();

  const { lockToken } = useLockGuard(doc_id || null);

  const fetchDoc = async () => {
    try {
      const res = await apiClient.get(`/documents/${doc_id}`);
      const doc = res.data.data;
      setDocMetadata(doc.doc_id, doc.doc_type_id, doc.doc_type_name, doc.status);
      setContent(doc.content || '');
      
      if (doc.ai_polished_content) {
        setPolishedResult(doc.ai_polished_content, doc.draft_suggestion);
      }

      if (doc.status !== 'DRAFTING') {
        setReadOnly(true, 'IMMUTABLE');
      }
    } catch (err) {
      message.error('加载公文失败');
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!doc_id) return;
    fetchDoc();
    return () => {
      resetEditor();
      if (polishTimeoutRef.current) {
        clearTimeout(polishTimeoutRef.current);
        polishTimeoutRef.current = null;
      }
    };
  }, [doc_id]);

  // 监听异步任务完成 (Task 2 & 4)
  useEffect(() => {
    if (currentTaskId && taskResults[currentTaskId]) {
      const result = taskResults[currentTaskId];
      if (polishTimeoutRef.current) {
        clearTimeout(polishTimeoutRef.current);
        polishTimeoutRef.current = null;
      }
      if (result.event === 'task.completed' || result.task_status === 'COMPLETED') {
        fetchDoc().then(() => {
          message.success('AI 润色已就绪');
          setBusy(false);
          setCurrentTaskId(null);
        });
      } else if (result.event === 'task.failed' || result.task_status === 'FAILED') {
        message.error('AI 润色失败: ' + (result.error_message || '未知错误'));
        setBusy(false);
        setCurrentTaskId(null);
      }
    }
  }, [currentTaskId, taskResults]);

  useEffect(() => {
    if (!doc_id || isReadOnly || isBusy) return;

    const autoSave = async () => {
      const payload: any = { title: undefined };
      if (viewMode === 'SINGLE') {
        payload.content = content;
      } else {
        payload.draft_content = draftSuggestion;
      }

      try {
        await apiClient.post(`/documents/${doc_id}/auto-save`, payload);
      } catch (e) {
        console.error("Auto-save failed", e);
      }
    };

    const timer = setInterval(autoSave, 60000);
    return () => clearInterval(timer);
  }, [doc_id, content, draftSuggestion, viewMode, isReadOnly, isBusy]);

  const handlePolish = async () => {
    if (isBusy) return;
    setBusy(true);
    try {
      const snapRes = await apiClient.get('/kb/snapshot-version');
      const snapshotVersion = snapRes.data.data.snapshot_version;

      const res = await apiClient.post('/tasks/polish', {
        doc_id,
        context_kb_ids,
        context_snapshot_version: snapshotVersion,
        exemplar_id: exemplarId
      });

      const taskId = res.data.data.task_id;
      addTask(taskId);
      setCurrentTaskId(taskId);
      message.info('AI 润色任务已派发，请稍候...');

      // 5 分钟超时兜底
      polishTimeoutRef.current = window.setTimeout(() => {
        message.error('AI 润色超时，请检查服务状态后重试');
        setBusy(false);
        setCurrentTaskId(null);
      }, 300000);
    } catch (e) {
      setBusy(false);
    }
  };

  const handleApplyPolish = async () => {
    setBusy(true);
    try {
      await apiClient.post(`/documents/${doc_id}/apply-polish`, {
        final_content: draftSuggestion
      });
      message.success('已应用 AI 润色建议');
      setContent(draftSuggestion || '');
      setPolishedResult(null, null);
      setViewMode('SINGLE');
    } finally {
      setBusy(false);
    }
  };

  const handleDiscardPolish = async () => {
    setBusy(true);
    try {
      await apiClient.post(`/documents/${doc_id}/discard-polish`);
      setPolishedResult(null, null);
      setViewMode('SINGLE');
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = async () => {
    if (isBusy) return;
    Modal.confirm({
      title: '确认提交审批？',
      content: '提交后将锁定编辑，进入科长待办。',
      onOk: async () => {
        setBusy(true);
        try {
          await apiClient.post(`/documents/${doc_id}/submit`);
          message.success('提交成功');
          navigate('/dashboard');
        } finally {
          setBusy(false);
        }
      }
    });
  };

  if (loading) return <div className="workspace-loading"><Spin size="large" tip="正在进入沉浸式工作区..." /></div>;

  return (
    <Layout className="workspace-layout">
      {isReadOnly && (
        <div className={`readonly-banner ${readOnlyReason === 'CONFLICT' ? 'warning' : 'info'}`}>
          {readOnlyReason === 'CONFLICT' ? '⚠️ 正在有他人编辑此文档，当前仅限只读' : '📘 公文已归档/流转中，不可编辑'}
        </div>
      )}

      <Header className="workspace-header">
        <Space size="large">
          <Button type="text" icon={<LeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
          <div className="doc-info">
            <span className="doc-title">{content.split('\n')[0]?.substring(0, 20) || '未命名公文'}</span>
            <Tag color="blue">{docTypeName || '通用文种'}</Tag>
          </div>
        </Space>

        <Space>
          <Button icon={<HistoryOutlined />} onClick={() => setSnapshotDrawerOpen(true)}>历史快照</Button>
          <div className="divider" />
          <Button 
            type="primary" 
            className="btn-polish" 
            icon={<BulbOutlined />}
            onClick={handlePolish}
            loading={isBusy && viewMode === 'SINGLE'}
            disabled={isReadOnly}
          >
            AI 智能润色
          </Button>
          <Button icon={<DownloadOutlined />} disabled={isReadOnly}>GB国标排版</Button>
          <Button 
            type="primary" 
            icon={<SendOutlined />} 
            style={{ background: '#003366' }}
            onClick={handleSubmit}
            disabled={isReadOnly || isBusy}
          >
            提交审批
          </Button>
        </Space>
      </Header>

      <Layout style={{ height: `calc(100vh - 64px - ${isReadOnly ? '32px' : '0px'})` }}>
        <Sider width={280} theme="light" className="workspace-sider">
          <div className="sider-section">
             <h4 style={{ marginBottom: '12px' }}>台账挂载 (RAG)</h4>
             <VirtualDocTree />
          </div>
          <div className="sider-section bottom">
             <h4 style={{ marginBottom: '12px' }}>📄 参考范文</h4>
             <ExemplarPanel />
          </div>
        </Sider>

        <Content className="workspace-content" ref={containerRef}>
          <div className="editor-viewport-inner" style={{ 
            transform: `scale(${scale})`, 
            transformOrigin: 'top center',
            transition: 'transform 0.2s ease-out'
          }}>
            <EditorA4Paper>
              {viewMode === 'SINGLE' ? (
                <textarea 
                  className="markdown-editor" 
                  value={content} 
                  onChange={(e) => setContent(e.target.value)}
                  readOnly={isReadOnly}
                  placeholder="在此输入公文正文..."
                />
              ) : (
                <div className="diff-mode-container">
                  <div className="diff-col left">
                    <div className="diff-label">只读原稿</div>
                    <textarea className="diff-editor readonly" value={content} readOnly />
                  </div>
                  <div className="diff-col right">
                    <div className="diff-label">AI 建议稿 (可修改)</div>
                    <textarea 
                        className="diff-editor" 
                        value={draftSuggestion || ''} 
                        onChange={(e) => setDraftSuggestion(e.target.value)}
                    />
                  </div>
                  <div className="diff-actions">
                    <Space size="large">
                      <Popconfirm title="确认接受 AI 建议？这将会覆盖当前正文。" onConfirm={handleApplyPolish}>
                        <Button type="primary" size="large" loading={isBusy}>接受并合并</Button>
                      </Popconfirm>
                      <Popconfirm title="确认丢弃 AI 建议？" onConfirm={handleDiscardPolish}>
                        <Button size="large" disabled={isBusy}>丢弃建议</Button>
                      </Popconfirm>
                    </Space>
                  </div>
                </div>
              )}
            </EditorA4Paper>
          </div>
        </Content>
      </Layout>

      <SnapshotRecoveryDrawer 
        open={snapshotDrawerOpen} 
        onClose={() => setSnapshotDrawerOpen(false)} 
      />
    </Layout>
  );
};