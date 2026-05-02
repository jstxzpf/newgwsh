import React, { useEffect, useState, useMemo } from 'react';
import { Row, Col, Button, List, Tag, Statistic, Space, Skeleton, Typography, theme, message, Alert } from 'antd';
import { PlusOutlined, EditOutlined, CheckCircleOutlined, ClockCircleOutlined, DashboardOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { documentService, sysService, DocumentRecord, DashboardStats } from '../api/services';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { userInfo } = useAuthStore();
  const { token } = theme.useToken();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [docsRes, statsRes] = await Promise.all([
        documentService.getList({ page_size: 5 }),
        sysService.getStats()
      ]);
      // [P0] harden: 由于拦截器已解构 res.data，直接使用 res
      setDocs(docsRes.items || []);
      setStats(statsRes); 
    } catch (err: any) {
      setError('无法获取工作台实时数据，请检查网络连接');
      console.error('Dashboard data error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // [P2] colorize: 对齐品牌色状态标签
  const getStatusTag = (status: string) => {
    switch (status) {
      case 'DRAFTING': case '起草中': 
        return <Tag icon={<ClockCircleOutlined />} color="warning">起草中</Tag>;
      case 'SUBMITTED': case '审批中': 
        return <Tag icon={<ClockCircleOutlined />} color="processing">审批中</Tag>;
      case 'APPROVED': case '已通过': 
        return <Tag icon={<CheckCircleOutlined />} color="success">已通过</Tag>;
      default: 
        return <Tag color="default">{status}</Tag>;
    }
  };

  return (
    // [P0] layout: 引入“权威长卷”居中框架，移除通用的背景填充
    <div style={{ padding: token.paddingLG, backgroundColor: token.colorBgLayout, minHeight: '100%', overflowY: 'auto' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        
        {/* 顶部欢迎区 - 移除 SaaS 样式的深蓝 Banner，改用长卷页眉 */}
        <div style={{ 
          marginBottom: token.marginXL, 
          paddingBottom: token.paddingLG,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'flex-end' 
        }}>
          <div>
            <Space align="center" size="middle">
              <SafetyCertificateOutlined style={{ fontSize: 32, color: token.colorPrimary }} />
              <div>
                <Title level={3} style={{ margin: 0 }}>下午好，{userInfo?.full_name || '用户'}</Title>
                <Text type="secondary">所属科室: {userInfo?.department_name || '系统管理处'} | 公文处理中枢</Text>
              </div>
            </Space>
          </div>
          <Button 
            type="primary" 
            size="large" 
            icon={<PlusOutlined />} 
            onClick={() => navigate('/documents')}
            style={{ borderRadius: token.borderRadiusSM }}
          >
            起草新公文
          </Button>
        </div>

        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: token.marginLG }} action={<Button size="small" onClick={fetchData}>重试</Button>} />}

        <Row gutter={[token.marginLG, token.marginLG]}>
          {/* 左侧：核心动态长卷 */}
          <Col lg={16} md={24}>
            <div style={{ 
              backgroundColor: token.colorBgContainer, 
              padding: token.paddingLG, 
              borderRadius: token.borderRadiusSM,
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: token.marginLG }}>
                <Title level={5} style={{ margin: 0 }}>
                  <Space><DashboardOutlined /> 最近处理</Space>
                </Title>
                <Button type="link" onClick={() => navigate('/documents')}>查看全部</Button>
              </div>
              
              <List
                loading={loading}
                dataSource={docs}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Button type="link" icon={<EditOutlined />} onClick={() => navigate(`/workspace/${item.doc_id}`)}>进入工作区</Button>
                    ]}
                  >
                    <List.Item.Meta
                      title={<Text strong>{item.title}</Text>}
                      description={`最后操作: ${new Date(item.updated_at).toLocaleString()}`}
                    />
                    <div>{getStatusTag(item.status)}</div>
                  </List.Item>
                )}
              />
            </div>
          </Col>

          {/* 右侧：统计与负载监控 */}
          <Col lg={8} md={24}>
            <Space direction="vertical" style={{ width: '100%' }} size={token.marginLG}>
              {/* 关键指标：遵循“权威长卷”的扁平化原则 */}
              <div style={{ 
                backgroundColor: token.colorBgContainer, 
                padding: token.paddingLG, 
                borderRadius: token.borderRadiusSM,
                boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
              }}>
                <Title level={5} style={{ marginBottom: token.marginMD }}>快捷统计</Title>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic 
                      title="待我处理" 
                      value={stats?.pending_tasks || 0} 
                      valueStyle={{ color: token.colorError }} 
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic 
                      title="本月结转" 
                      value={stats?.document_counts?.APPROVED || 0} 
                      valueStyle={{ color: token.colorPrimary }}
                    />
                  </Col>
                </Row>
              </div>

              {/* 引擎负载：细节打磨 */}
              <div style={{ 
                backgroundColor: token.colorBgContainer, 
                padding: token.paddingLG, 
                borderRadius: token.borderRadiusSM,
                boxShadow: '0 1px 2px rgba(0,0,0,0.03)'
              }}>
                <Title level={5} style={{ marginBottom: token.marginMD }}>系统引擎状态</Title>
                {loading ? <Skeleton active paragraph={{ rows: 2 }} /> : (
                  <List
                    size="small"
                    dataSource={[
                      { name: 'AI 联机引擎', progress: stats?.ai_engine_online ? 15 : 0, color: token.colorSuccess },
                      { name: '系统资源调度', progress: 45, color: token.colorInfo },
                    ]}
                    renderItem={(item) => (
                      <List.Item style={{ padding: '8px 0', border: 'none' }}>
                        <div style={{ width: '100%' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                            <Text size="small">{item.name}</Text>
                            <Text size="small" type="secondary">{item.progress}%</Text>
                          </div>
                          <div style={{ height: 4, background: token.colorFillTertiary, borderRadius: 2 }}>
                            <div style={{ 
                              height: '100%', 
                              width: `${item.progress}%`, 
                              background: item.color, 
                              borderRadius: 2,
                              transition: 'all 0.3s'
                            }} />
                          </div>
                        </div>
                      </List.Item>
                    )}
                  />
                )}
              </div>
            </Space>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default Dashboard;
