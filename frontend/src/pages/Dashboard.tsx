import React, { useEffect, useState } from 'react';
import { Layout, Button, Card, Typography, List, Tag, message, Skeleton } from 'antd';
import { PlusOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';
import { useEditorStore } from '../store/useEditorStore';

const { Header, Content } = Layout;
const { Title } = Typography;

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const userInfo = useAuthStore(state => state.userInfo);
  const { setDocId } = useEditorStore();
  const [loading, setLoading] = useState(false);
  const [recentDrafts, setRecentDrafts] = useState([]);
  const [rejectedDocs, setRejectedDocs] = useState([]);
  const [approvals, setApprovals] = useState([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. 获取起草中的公文
      const resDrafts = await apiClient.get('/documents/', { params: { status: 'DRAFTING' } });
      setRecentDrafts(resDrafts.data.slice(0, 5));

      // 2. 获取被驳回的公文
      const resRejected = await apiClient.get('/documents/', { params: { status: 'REJECTED' } });
      setRejectedDocs(resRejected.data);

      // 3. 若是科长，获取待签批
      if (userInfo?.roleLevel >= 5) {
          const resApprovals = await apiClient.get('/documents/', { params: { status: 'SUBMITTED' } });
          setApprovals(resApprovals.data);
      }
    } catch (e) {
      console.error("数据加载失败", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [userInfo]);

  const handleStartDraft = async () => {
    try {
      const res = await apiClient.post('/documents/init', { title: "新公文草稿" });
      const newDocId = res.data.doc_id;
      setDocId(newDocId);
      navigate(`/workspace/${newDocId}`);
    } catch (e) {
      message.error("创建公文失败");
    }
  };

  const handleRevise = async (docId: string) => {
    try {
      const res = await apiClient.post(`/documents/${docId}/revise`);
      if (res.data.lock_acquired) {
        useEditorStore.getState().setPolishedContent(null);
        useEditorStore.getState().setViewMode('SINGLE');
        useEditorStore.getState().setContent('');
        setDocId(docId);
        sessionStorage.setItem(`lock_token:${docId}`, res.data.lock_token);
        navigate(`/workspace/${docId}`);
      }
    } catch (err) {
      message.error("获取编辑锁失败，可能已被锁定");
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }} aria-label="个人工作台容器">
      <Header style={{ background: '#ffffff', borderBottom: '1px solid #f0f0f0', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <h2 style={{ color: '#003366', margin: 0, fontSize: '18px', fontWeight: 'bold' }}>个人工作台 (Dashboard)</h2>
      </Header>
      
      {loading ? <Skeleton active style={{ padding: 24 }} /> : (
      <Content style={{ padding: '24px', background: 'var(--bg-workspace)', display: 'flex', gap: '24px' }}>
        <div style={{ flex: 2, display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <Card styles={{ body: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' } }}>
            <div>
              <Title level={4} style={{ margin: 0 }}>欢迎回来，{userInfo?.username}</Title>
              <div style={{ color: '#666', marginTop: '8px' }}>所属科室：{userInfo?.deptName || '未分配'}</div>
            </div>
            <Button 
              type="primary" 
              size="large" 
              icon={<PlusOutlined />} 
              style={{ backgroundColor: '#003366', height: '64px', borderRadius: '8px', border: 'none' }}
              onClick={handleStartDraft}
            >
              起草新公文
            </Button>
          </Card>
          
          <Card title="近期处理台 (Drafting)">
            <List
              dataSource={recentDrafts}
              renderItem={(item: any) => (
                <List.Item actions={[<Button type="link" onClick={() => navigate(`/workspace/${item.doc_id}`)}>继续编辑</Button>]}>
                  <List.Item.Meta
                    avatar={<FileTextOutlined style={{ fontSize: '24px', color: '#003366' }} />}
                    title={item.title}
                    description={<Tag color="processing">起草中</Tag>}
                  />
                </List.Item>
              )}
            />
          </Card>
        </div>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <Card title="任务聚焦板 (Rejected)" style={{ borderTop: '4px solid #ff4d4f' }}>
            <List
              dataSource={rejectedDocs} 
              locale={{ emptyText: '暂无被驳回的公文' }}
              renderItem={(item: any) => (
                <List.Item 
                  actions={[<Button type="primary" danger size="small" onClick={() => handleRevise(item.doc_id)}>唤醒修改</Button>]}
                  style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', background: '#fff2f0', padding: '12px', borderRadius: '4px', marginBottom: '8px', border: '1px solid #ffccc7' }}
                >
                  <div style={{ fontWeight: 'bold', fontSize: '14px', color: '#cf1322' }}>{item.title}</div>
                </List.Item>
              )}
            />
          </Card>
          
          {userInfo?.roleLevel >= 5 && (
            <Card title="待我签批 (Approvals)" style={{ borderTop: '4px solid #52c41a' }}>
              <List
                dataSource={approvals} 
                locale={{ emptyText: '本科室暂无待签批公文' }}
                renderItem={(item: any) => (
                  <List.Item onClick={() => navigate('/approvals')} style={{ cursor: 'pointer' }}>
                      {item.title}
                  </List.Item>
                )}
              />
              <Button type="dashed" block style={{ marginTop: '16px' }} onClick={() => navigate('/approvals')}>
                进入签批管控台 &rarr;
              </Button>
            </Card>
          )}
        </div>
      </Content>
      )}
    </Layout>
  );
};
