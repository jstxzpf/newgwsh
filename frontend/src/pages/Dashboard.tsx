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
      <Header style={{ background: '#ffffff', borderBottom: '1px solid #f0f0f0', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <h2 style={{ color: '#003366', margin: 0, fontSize: '18px', fontWeight: 'bold' }}>个人工作台 (Dashboard)</h2>
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
              dataSource={[{ id: 'demo-123', title: '2024年一季度农业总产值分析报告', status: 'DRAFTING', updated_at: '2026-04-25 10:00' }]}
              renderItem={item => (
                <List.Item actions={[<Button type="link" onClick={() => navigate(`/workspace/${item.id}`)}>继续编辑</Button>]}>
                  <List.Item.Meta
                    avatar={<FileTextOutlined style={{ fontSize: '24px', color: '#003366' }} />}
                    title={item.title}
                    description={
                        <>
                            <Tag color="processing">起草中</Tag>
                            <span style={{ fontSize: '12px', color: '#888' }}>最后修改: {item.updated_at}</span>
                        </>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </div>

        {/* 右侧关注板 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <Card title="任务聚焦板 (Rejected)" style={{ borderTop: '4px solid #ff4d4f' }}>
            <List
              dataSource={[
                { id: 'reject-1', title: '关于二季度工业指标的请示', reason: '数据与最新统计口径不符，请重新核对后提交。', time: '2026-04-24 15:30' }
              ]} 
              locale={{ emptyText: '暂无被驳回的公文' }}
              renderItem={item => (
                <List.Item 
                  actions={[
                    <Button 
                      type="primary" 
                      danger 
                      size="small" 
                      onClick={() => navigate(`/workspace/${item.id}`)}
                    >
                      唤醒修改 (Revise)
                    </Button>
                  ]}
                  style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', background: '#fff2f0', padding: '12px', borderRadius: '4px', marginBottom: '8px', border: '1px solid #ffccc7' }}
                >
                  <div style={{ fontWeight: 'bold', fontSize: '14px', marginBottom: '4px', color: '#cf1322' }}>{item.title}</div>
                  <div style={{ fontSize: '12px', color: '#555', marginBottom: '8px' }}>驳回时间: {item.time}</div>
                  <div style={{ fontSize: '13px', color: '#ff4d4f', background: '#fff', padding: '8px', borderRadius: '4px', width: '100%' }}>
                    <strong>驳回理由：</strong>{item.reason}
                  </div>
                </List.Item>
              )}
            />
          </Card>
          
          {userInfo?.roleLevel && userInfo.roleLevel >= 5 && (
            <Card title="待我签批 (Approvals)" style={{ borderTop: '4px solid #52c41a' }}>
              <List
                dataSource={[]} 
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
