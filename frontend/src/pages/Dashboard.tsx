import React from 'react';
import { Layout, Button, Card, Typography, List, Tag } from 'antd';
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

  const handleStartDraft = async () => {
    try {
      const res = await apiClient.post('/documents/init', { title: "新公文草稿" });
      const newDocId = res.data.doc_id;
      setDocId(newDocId);
      navigate(`/workspace/${newDocId}`);
    } catch (e) {
      console.error("创建公文失败", e);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#003366', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <h2 style={{ color: '#fff', margin: 0, fontSize: '18px' }}>个人工作台 (Dashboard)</h2>
      </Header>
      <Content style={{ padding: '24px', background: 'var(--bg-workspace)', display: 'flex', gap: '24px' }}>
        
        {/* 左侧卡片瀑布流 */}
        <div style={{ flex: 2, display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <Card styles={{ body: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' } }}>
            <div>
              <Title level={4} style={{ margin: 0 }}>欢迎回来，{userInfo?.username}</Title>
              <div style={{ color: '#666', marginTop: '8px' }}>准备好起草新的政务公文了吗？</div>
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
              dataSource={[{ id: 'demo-123', title: '2024年一季度农业总产值分析报告', status: 'DRAFTING' }]}
              renderItem={item => (
                <List.Item actions={[<Button type="link" onClick={() => navigate(`/workspace/${item.id}`)}>继续编辑</Button>]}>
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

        {/* 右侧关注板 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <Card title="任务聚焦板 (Rejected)">
            <List
              dataSource={[]} // TODO: Fetch from API
              locale={{ emptyText: '暂无被驳回的公文' }}
              renderItem={() => <List.Item></List.Item>}
            />
          </Card>
          
          {userInfo?.roleLevel && userInfo.roleLevel >= 5 && (
            <Card title="待我签批 (Approvals)" style={{ borderTop: '4px solid #52c41a' }}>
              <List
                dataSource={[]} // TODO: Fetch from API
                locale={{ emptyText: '本科室暂无待签批公文' }}
                renderItem={() => <List.Item></List.Item>}
              />
              <Button type="dashed" block style={{ marginTop: '16px' }} onClick={() => navigate('/approvals')}>
                进入签批管控台 &rarr;
              </Button>
            </Card>
          )}
        </div>
      </Content>
    </Layout>
  );
};
