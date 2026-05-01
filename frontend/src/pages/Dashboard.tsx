import React from 'react';
import { Row, Col, Card, Button, List, Tag, Statistic, Space } from 'antd';
import { PlusOutlined, EditOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const mockTasks = [
    { id: 1, title: '关于2024年一季度数据的分析报告', status: 'DRAFTING', type: '调研分析', time: '10分钟前' },
    { id: 2, title: '泰兴调查队安全生产工作通知', status: 'SUBMITTED', type: '通知', time: '1小时前' },
    { id: 3, title: '2023年度工作总结', status: 'APPROVED', type: '报告', time: '昨天' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Row gutter={[24, 24]}>
        <Col span={24}>
          <Card bordered={false} style={{ background: '#003366', color: '#fff' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ color: '#fff', margin: 0 }}>下午好，系统管理员</h2>
                <p style={{ margin: '8px 0 0', opacity: 0.8 }}>今天是 2026年5月1日 星期五 | 欢迎回到公文处理中枢</p>
              </div>
              <Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => navigate('/documents')} style={{ background: '#fff', color: '#003366', border: 'none' }}>
                起草新公文
              </Button>
            </div>
          </Card>
        </Col>

        <Col span={16}>
          <Card title="任务聚焦板" extra={<a href="#">更多</a>}>
            <List
              dataSource={mockTasks}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    <Button type="link" icon={<EditOutlined />} onClick={() => navigate(`/workspace/${item.id}`)}>编辑</Button>
                  ]}
                >
                  <List.Item.Meta
                    title={<span>{item.title} <Tag color="blue">{item.type}</Tag></span>}
                    description={`更新时间: ${item.time}`}
                  />
                  <div>
                    {item.status === 'DRAFTING' && <Tag icon={<ClockCircleOutlined />} color="warning">起草中</Tag>}
                    {item.status === 'SUBMITTED' && <Tag icon={<ClockCircleOutlined />} color="processing">审批中</Tag>}
                    {item.status === 'APPROVED' && <Tag icon={<CheckCircleOutlined />} color="success">已通过</Tag>}
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col span={8}>
          <Space direction="vertical" style={{ width: '100%' }} size={24}>
            <Card title="快捷统计">
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title="待我签批" value={3} valueStyle={{ color: '#cf1322' }} />
                </Col>
                <Col span={12}>
                  <Statistic title="起草中" value={5} />
                </Col>
              </Row>
            </Card>
            <Card title="异步任务中心">
              <List
                size="small"
                dataSource={[
                  { name: 'AI 润色', progress: 100, status: 'success' },
                  { name: '国标排版', progress: 45, status: 'active' },
                ]}
                renderItem={(item) => (
                  <List.Item>
                    <div style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span>{item.name}</span>
                        <span>{item.progress}%</span>
                      </div>
                      <div style={{ height: 4, background: '#f5f5f5', borderRadius: 2 }}>
                        <div style={{ height: '100%', width: `${item.progress}%`, background: item.status === 'success' ? '#52c41a' : '#1890ff', borderRadius: 2 }} />
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
