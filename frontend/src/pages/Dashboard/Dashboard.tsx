import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, List, Badge, Button, Typography, Space, Modal, Form, Input, Select } from 'antd';
import { 
  FileTextOutlined, 
  CheckCircleOutlined, 
  ClockCircleOutlined, 
  ExclamationCircleOutlined,
  PlusOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { apiClient } from '../../api/client';

const { Title } = Typography;

export const Dashboard: React.FC = () => {
  const userInfo = useAuthStore(state => state.userInfo);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [statsData, setStatsData] = useState({ drafted: 0, submitted: 0, reviewed: 0, rejected: 0, approved: 0, archived: 0 });
  const [recentDocs, setRecentDocs] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, docsRes] = await Promise.all([
          apiClient.get('/documents/dashboard/stats'),
          apiClient.get('/documents?page=1&page_size=5')
        ]);
        setStatsData(statsRes.data.data);
        setRecentDocs(docsRes.data.data.items);
      } catch (e) {
        console.error("Failed to fetch dashboard data", e);
      }
    };
    fetchData();
  }, []);

  const handleCreate = async (values: any) => {
    try {
      const res = await apiClient.post('/documents/init', values);
      const docId = res.data.data.doc_id;
      setIsModalOpen(false);
      navigate(`/workspace/${docId}`);
    } catch (e) {
      // 错误已由拦截器处理
    }
  };

  const stats = [
    { title: '我起草的', value: statsData.drafted, icon: <FileTextOutlined />, color: '#1890ff' },
    { title: '待科长审核', value: statsData.submitted, icon: <ClockCircleOutlined />, color: '#faad14' },
    { title: '待局长签发', value: statsData.reviewed, icon: <ClockCircleOutlined />, color: '#13c2c2' },
    { title: '被驳回', value: statsData.rejected, icon: <ExclamationCircleOutlined />, color: '#ff4d4f' },
    { title: '已签发', value: statsData.approved, icon: <CheckCircleOutlined />, color: '#52c41a' },
    { title: '已归档', value: statsData.archived, icon: <CheckCircleOutlined />, color: '#8c8c8c' },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>你好，{userInfo?.full_name}</Title>
          <Typography.Text type="secondary">{userInfo?.department_name} | {userInfo?.role_level === 99 ? '系统管理员' : '公文处理员'}</Typography.Text>
        </div>
        <Button 
          type="primary" 
          size="large" 
          icon={<PlusOutlined />} 
          style={{ height: '48px', padding: '0 32px' }}
          onClick={() => setIsModalOpen(true)}
        >
          起草新公文
        </Button>
      </div>

      <Modal
        title="起草新公文"
        open={isModalOpen}
        onOk={() => form.submit()}
        onCancel={() => setIsModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="title" label="公文标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input placeholder="请输入公文标题" />
          </Form.Item>
          <Form.Item name="doc_type_id" label="文种类型" rules={[{ required: true, message: '请选择文种' }]}>
            <Select placeholder="请选择文种">
              <Select.Option value={1}>通知</Select.Option>
              <Select.Option value={2}>报告</Select.Option>
              <Select.Option value={3}>请示</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Row gutter={16}>
        {stats.map((item, index) => (
          <Col span={4} key={index}>
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
          <Card title="最近起草" extra={<a href="/documents" onClick={(e) => { e.preventDefault(); navigate('/documents'); }}>查看全部</a>}>
            <List
              itemLayout="horizontal"
              dataSource={recentDocs}
              renderItem={item => (
                <List.Item actions={[<Button type="link" onClick={() => navigate(`/workspace/${item.doc_id}`)}>继续编辑</Button>]}>
                  <List.Item.Meta
                    title={item.title}
                    description={
                      <Space>
                        <Badge status={item.status === 'DRAFTING' ? 'processing' : (item.status === 'SUBMITTED' || item.status === 'REVIEWED' ? 'warning' : 'default')} text={{DRAFTING:'起草中',SUBMITTED:'待科长审核',REVIEWED:'科长已审',APPROVED:'已签发',REJECTED:'已驳回',ARCHIVED:'已归档'}[item.status] || item.status} />
                        <Typography.Text type="secondary">{new Date(item.created_at).toLocaleString()}</Typography.Text>
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