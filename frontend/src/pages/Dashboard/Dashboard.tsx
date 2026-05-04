import React from 'react';
import { Card, Row, Col, Statistic, List, Badge, Button, Typography, Space } from 'antd';
import { 
  FileTextOutlined, 
  CheckCircleOutlined, 
  ClockCircleOutlined, 
  ExclamationCircleOutlined,
  PlusOutlined
} from '@ant-design/icons';
import { useAuthStore } from '../../stores/authStore';

const { Title } = Typography;

export const Dashboard: React.FC = () => {
  const userInfo = useAuthStore(state => state.userInfo);

  // 模拟数据（后续对接 API）
  const stats = [
    { title: '我起草的', value: 12, icon: <FileTextOutlined />, color: '#1890ff' },
    { title: '待签批', value: 3, icon: <ClockCircleOutlined />, color: '#faad14' },
    { title: '被驳回', value: 1, icon: <ExclamationCircleOutlined />, color: '#ff4d4f' },
    { title: '已归档', value: 45, icon: <CheckCircleOutlined />, color: '#52c41a' },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>你好，{userInfo?.full_name}</Title>
          <Typography.Text type="secondary">{userInfo?.department_name} | {userInfo?.role_level === 99 ? '系统管理员' : '公文处理员'}</Typography.Text>
        </div>
        <Button type="primary" size="large" icon={<PlusOutlined />} style={{ height: '48px', padding: '0 32px' }}>
          起草新公文
        </Button>
      </div>

      <Row gutter={16}>
        {stats.map((item, index) => (
          <Col span={6} key={index}>
            <Card hoverable>
              <Statistic 
                title={item.title} 
                value={item.value} 
                prefix={React.cloneElement(item.icon as React.ReactElement, { style: { color: item.color } })} 
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={24} style={{ marginTop: '24px' }}>
        <Col span={16}>
          <Card title="最近起草" extra={<a href="/documents">查看全部</a>}>
            <List
              itemLayout="horizontal"
              dataSource={[
                { title: '关于2024年一季度统计数据核查的通知', status: 'DRAFTING', time: '2小时前' },
                { title: '泰兴队2024年安全生产工作计划', status: 'SUBMITTED', time: '昨天' },
              ]}
              renderItem={item => (
                <List.Item actions={[<Button type="link">继续编辑</Button>]}>
                  <List.Item.Meta
                    title={item.title}
                    description={
                      <Space>
                        <Badge status={item.status === 'DRAFTING' ? 'processing' : 'warning'} text={item.status === 'DRAFTING' ? '起草中' : '审核中'} />
                        <Typography.Text type="disabled">{item.time}</Typography.Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="快捷通知" style={{ height: '100%' }}>
             <Typography.Text type="secondary">暂无新通知</Typography.Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
};