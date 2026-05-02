import React, { useEffect, useRef, useState } from 'react';
import { Layout, Button, Space, Tag, Divider, Tree, message, Popconfirm, Alert, Skeleton, theme, Typography } from 'antd';
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
import { documentService, taskService, DocumentRecord } from '../api/services';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

const Workspace: React.FC = () => {
  const { doc_id } = useParams<{ doc_id: string }>();
  const navigate = useNavigate();
  const { token: antdToken } = theme.useToken();
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
  
  const { token: authToken } = useAuthStore();
  const { isReadOnly, readOnlyReason, acquireLock, lockToken } = useLockGuard(doc_id || null);

  useEffect(() => {
    (window as any).__LOCK_TOKEN__ = lockToken;
  }, [lockToken]);

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
        .then((res: DocumentRecord) => {
          // [P0] harden: 由于拦截器已解构 res.data，直接使用 res
          setContent(res.content || '');
          setDocStatus(res.status);
          
          // Resume DIFF mode if cloud has unapplied AI suggestions
          if (res.ai_polished_content || res.draft_suggestion) {
             setAiPolishedContent(res.draft_suggestion || res.ai_polished_content || null);
             setViewMode('DIFF');
          } else {
             setViewMode('SINGLE');
          }
        })
        .catch(() => message.error('无法加载文档，请重试'));
    }
  }, [doc_id, setContent, setDocStatus, setAiPolishedContent, setViewMode]);

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
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify(payload),
          keepalive: true
        });
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [doc_id, lockToken, content, aiPolishedContent, isReadOnly, viewMode, authToken]);

  const handleInputFocus = () => {
    console.log('handleInputFocus triggered', { isReadOnly, docStatus, lockToken });
    // DRAFTING is 10 in backend IntEnum
    if (!isReadOnly && (docStatus === 'DRAFTING' || docStatus === 10 || (docStatus as any) === '10')) {
      if (!lockToken) {
        acquireLock();
      }
    }
  };

  const handlePolish = async () => {
    console.log('handlePolish called', { doc_id, lockToken, docStatus });
    if (!doc_id || !lockToken) {
      if (docStatus === 'DRAFTING' || docStatus === 10 || (docStatus as any) === '10') {
        message.warning('请先点击正文获取编辑权限再进行润色');
      } else {
        message.error('当前状态不支持润色');
      }
      return;
    }
    setBusy(true);
    message.loading('AI 正在研读挂载台账，请稍候...');
    try {
      await taskService.startPolish({
         doc_id,
         lock_token: lockToken,
         context_kb_ids: [], // To be wired to Tree
         context_snapshot_version: Date.now(), // Mocking snapshot version
      });
      // The GlobalTaskWatcher will handle the SSE push and UI state update
    } catch (err) {
      message.error('发起润色失败，请重试');
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
      message.error('应用建议失败，请重试');
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
       message.error('操作失败，请重试');
    } finally {
       setBusy(false);
    }
  };

  const handleSubmit = async () => {
    if (!doc_id) return;
    setBusy(true);
    try {
      await documentService.submit(doc_id);
      message.success('已成功提交审批');
      setDocStatus('SUBMITTED');
      navigate('/documents');
    } catch (err) {
      message.error('提交审批失败，请重试');
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
    // [P0] layout/colorize: 全局使用 token 的颜色
    <Layout style={{ height: 'calc(100vh - 64px - 24px)', background: antdToken.colorBgLayout }}>
      {/* Sidebar for KB Tree */}
      <Sider width={280} theme="dark" style={{ overflow: 'auto' }}>
        <div style={{ padding: antdToken.paddingMD }}>
          <Title level={5} style={{ margin: 0, color: 'rgba(255,255,255,0.85)' }}>知识资产挂载</Title>
          <Divider style={{ margin: `${antdToken.marginSM}px 0`, borderColor: 'rgba(255,255,255,0.1)' }} />
          <Tree
            checkable
            selectable={false}
            theme="dark"
            style={{ background: 'transparent', color: 'rgba(255,255,255,0.85)' }}
            treeData={[
              { title: '全局库', key: 'base', children: [{ title: '统计法.pdf', key: 'kb-1' }] },
              { title: '科室共享', key: 'dept', children: [{ title: '2024一季度分析.docx', key: 'kb-2' }] },
            ]}
          />
          <Divider style={{ margin: `${antdToken.marginLG}px 0 ${antdToken.marginSM}px`, borderColor: 'rgba(255,255,255,0.1)' }} />
          <Title level={5} style={{ margin: 0, color: 'rgba(255,255,255,0.85)', marginBottom: antdToken.marginSM }}>参考范文</Title>
          <div style={{ 
            padding: antdToken.paddingSM, 
            border: `1px dashed rgba(255,255,255,0.3)`, 
            borderRadius: antdToken.borderRadiusSM, 
            textAlign: 'center', 
            color: 'rgba(255,255,255,0.65)'
          }}>
            未选择范文
          </div>
        </div>
      </Sider>

      <Layout>
        {/* Top Action Bar */}
        <div style={{ 
          background: antdToken.colorBgContainer, 
          padding: `${antdToken.paddingSM}px ${antdToken.paddingLG}px`, 
          display: 'flex', 
          flexDirection: 'column', 
          borderBottom: `1px solid ${antdToken.colorBorderSecondary}`,
          boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
          zIndex: 1
        }}>
          
          {/* Read Only Banner */}
          {isReadOnly && (
             <Alert 
               message={readOnlyReason || '文档当前处于只读模式'} 
               type={docStatus !== 'DRAFTING' ? 'info' : 'warning'} 
               showIcon 
               style={{ marginBottom: antdToken.marginSM, width: '100%', justifyContent: 'center' }} 
               banner
             />
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <Space size="middle">
              <Button type="text" icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')} style={{ padding: 0 }}>返回</Button>
              <Divider type="vertical" />
              <Tag color="default" style={{ border: `1px solid ${antdToken.colorPrimary}`, color: antdToken.colorPrimary, backgroundColor: `${antdToken.colorPrimary}08` }}>调研分析</Tag>
              <Text type="secondary" style={{ fontSize: antdToken.fontSizeSM }}>文档ID: {doc_id}</Text>
            </Space>

            <Space>
              {viewMode === 'SINGLE' ? (
                <>
                  <Button icon={<HistoryOutlined />}>历史快照</Button>
                  <Button 
                    type="primary" 
                    icon={<ThunderboltOutlined />} 
                    onClick={handlePolish} 
                    loading={isBusy} 
                    disabled={isReadOnly}
                    // [P2] colorize: 移除硬编码紫色，使用主题主色
                  >
                    AI 智能润色
                  </Button>
                  {docStatus === 'APPROVED' ? (
                     <Button icon={<DownloadOutlined />} onClick={handleDownload}>下载国标文档 📥</Button>
                  ) : (
                     <Button icon={<DownloadOutlined />}>排版预览</Button>
                  )}
                  <Button 
                    type="primary" 
                    onClick={handleSubmit} 
                    loading={isBusy} 
                    disabled={isReadOnly || docStatus !== 'DRAFTING'}
                  >
                    提交审批
                  </Button>
                </>
              ) : (
                <Space>
                  <Button type="primary" icon={<CheckOutlined />} onClick={handleApplyPolish} loading={isBusy}>接受并合并</Button>
                  <Popconfirm title="确定丢弃 AI 润色建议吗？" onConfirm={handleDiscardPolish}>
                    <Button icon={<CloseOutlined />} danger loading={isBusy}>丢弃</Button>
                  </Popconfirm>
                </Space>
              )}
            </Space>
          </div>
        </div>

        {/* Paper Container */}
        <Content ref={containerRef} style={{ overflow: 'auto', padding: `${antdToken.paddingXL}px 0`, position: 'relative' }}>
          {/* Skeleton Pacifier */}
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
              paddingTop: antdToken.paddingXL,
              background: `${antdToken.colorBgLayout}80` // 50% opacity, removed blur to adhere to flat design
            }}>
              <div className="a4-paper" style={{ transform: `scale(${scale})`, transformOrigin: 'top center', padding: '72px 90px' }}>
                <Skeleton active paragraph={{ rows: 20 }} />
                <div style={{ 
                  position: 'absolute', 
                  top: '40%', 
                  left: 0, 
                  width: '100%', 
                  textAlign: 'center',
                  fontWeight: 600,
                  fontSize: 18,
                  color: antdToken.colorPrimary
                  // removed textShadow to adhere to flat design
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
                style={{ 
                  width: '100%', 
                  height: '100%', 
                  border: 'none', 
                  outline: 'none', 
                  resize: 'none', 
                  background: 'transparent',
                  fontFamily: 'inherit',
                  fontSize: 'inherit',
                  lineHeight: 'inherit'
                }}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onFocus={handleInputFocus}
                readOnly={isReadOnly}
                placeholder={isReadOnly ? "" : "在此开始起草公文..."}
              />
            ) : (
              // [P1] layout: 优化 DIFF 模式，使用主题色和更好的排版
              <div style={{ display: 'flex', gap: 40, height: '100%' }}>
                <div style={{ 
                  flex: 1, 
                  padding: antdToken.paddingMD, 
                  background: antdToken.colorFillQuaternary, 
                  borderRadius: antdToken.borderRadiusSM, 
                  cursor: 'not-allowed' 
                }}>
                  <div style={{ color: antdToken.colorTextDescription, marginBottom: antdToken.marginSM, fontSize: antdToken.fontSizeSM, fontWeight: 500 }}>[只读原稿]</div>
                  <div style={{ whiteSpace: 'pre-wrap', opacity: 0.8 }}>{content}</div>
                </div>
                <div style={{ 
                  flex: 1, 
                  padding: antdToken.paddingMD, 
                  background: antdToken.colorSuccessBg, 
                  border: `1px solid ${antdToken.colorSuccessBorder}`, 
                  borderRadius: antdToken.borderRadiusSM 
                }}>
                  <div style={{ color: antdToken.colorSuccessText, marginBottom: antdToken.marginSM, fontSize: antdToken.fontSizeSM, fontWeight: 500 }}>[AI 建议稿 - 可在此直接编辑]</div>
                  <textarea
                    style={{ 
                      width: '100%', 
                      height: 'calc(100% - 24px)', 
                      border: 'none', 
                      outline: 'none', 
                      resize: 'none', 
                      background: 'transparent',
                      fontFamily: 'inherit',
                      fontSize: 'inherit',
                      lineHeight: 'inherit',
                      color: antdToken.colorText
                    }}
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
