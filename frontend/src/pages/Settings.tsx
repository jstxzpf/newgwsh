import React, { useEffect, useState } from 'react';
import { Layout, Typography, Table, Tag, Button, Space, Card, Modal, Form, Input, Select, message, Tabs, Descriptions, Popconfirm, Statistic, Row, Col, Empty } from 'antd';
import { 
  UserOutlined, 
  SafetyOutlined, 
  LockOutlined, 
  DashboardOutlined, 
  SettingOutlined,
  UnlockOutlined,
  DeleteOutlined,
  SyncOutlined,
  PoweroffOutlined
} from '@ant-design/icons';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';
import dayjs from 'dayjs';

const { Content } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;

export const Settings: React.FC = () => {
  const userInfo = useAuthStore(state => state.userInfo);
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [locks, setLocks] = useState([]);
  const [sysStatus, setSysStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [userModalVisible, setUserModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<any>(null);
  const [form] = Form.useForm();

  const isAdmin = (userInfo?.roleLevel ?? 0) >= 99;

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'users' && isAdmin) {
        const res = await apiClient.get('/users/');
        setUsers(res.data);
      } else if (activeTab === 'locks' && isAdmin) {
        const res = await apiClient.get('/locks/');
        setLocks(res.data.locks);
      } else if (activeTab === 'system') {
        const res = await apiClient.get('/sys/status');
        setSysStatus(res.data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  // --- 用户管理逻辑 ---
  const handleEditUser = (user: any) => {
    setEditingUser(user);
    form.setFieldsValue({
      role_level: user.role_level,
      is_active: user.is_active,
    });
    setUserModalVisible(true);
  };

  const handleUpdateUser = async (values: any) => {
    try {
      await apiClient.put(`/users/${editingUser.user_id}`, values);
      message.success('用户信息已更新');
      setUserModalVisible(false);
      fetchData();
    } catch (e) {
      message.error('操作失败');
    }
  };

  // --- 强制夺锁逻辑 ---
  const handleForceUnlock = async (docId: string) => {
    try {
      await apiClient.delete(`/locks/lock:${docId}`);
      message.success('已强力释放该编辑锁');
      fetchData();
    } catch (e) {
      message.error('解锁失败');
    }
  };

  // --- 系统清理逻辑 ---
  const handleCleanup = async () => {
    try {
      await apiClient.post('/sys/cleanup-cache');
      message.success('临时文件与僵死缓存已肃清');
      fetchData();
    } catch (e) {
      message.error('清理失败');
    }
  };

  if (!isAdmin && activeTab !== 'system') {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <Card>
          <Empty 
            image={<SafetyOutlined style={{ fontSize: 64, color: '#ff4d4f' }} />}
            description={<Text type="danger">权限不足：系统中枢设置台仅对系统管理员开放</Text>}
          />
        </Card>
      </div>
    );
  }

  const userColumns = [
    { title: '工号', dataIndex: 'username', key: 'username' },
    { 
      title: '级别', 
      dataIndex: 'role_level', 
      key: 'role_level',
      render: (lv: number) => {
        if (lv >= 99) return <Tag color="gold">管理员</Tag>;
        if (lv >= 5) return <Tag color="blue">科长</Tag>;
        return <Tag>科员</Tag>;
      }
    },
    { 
      title: '状态', 
      dataIndex: 'is_active', 
      key: 'is_active',
      render: (active: boolean) => <Tag color={active ? 'green' : 'red'}>{active ? '启用' : '禁用'}</Tag>
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (d: any) => dayjs(d).format('YYYY-MM-DD') },
    { 
      title: '操作', 
      key: 'action', 
      render: (_: any, record: any) => (
        <Button size="small" type="link" onClick={() => handleEditUser(record)}>管理</Button>
      )
    }
  ];

  const lockColumns = [
    { title: '文档 ID', dataIndex: 'doc_id', key: 'doc_id', ellipsis: true },
    { title: '持锁人', dataIndex: 'username', key: 'username' },
    { title: '获取时间', dataIndex: 'acquired_at', key: 'acquired_at', render: (d: any) => dayjs(d).format('HH:mm:ss') },
    { 
      title: '操作', 
      key: 'action', 
      render: (_: any, record: any) => (
        <Popconfirm title="管理员强拆锁可能导致用户数据丢失，确定继续？" onConfirm={() => handleForceUnlock(record.doc_id)} okText="确定强拆" cancelText="取消" okButtonProps={{ danger: true }}>
          <Button type="link" danger icon={<UnlockOutlined />}>强行释放</Button>
        </Popconfirm>
      )
    }
  ];

  const items = [
    {
      key: 'users',
      label: <span><UserOutlined /> 用户与权限治理</span>,
      children: (
        <Table dataSource={users} columns={userColumns} rowKey="user_id" loading={loading} style={{ background: '#fff', borderRadius: 8 }} />
      )
    },
    {
      key: 'locks',
      label: <span><LockOutlined /> 并发死锁监控</span>,
      children: (
        <Table dataSource={locks} columns={lockColumns} rowKey="doc_id" loading={loading} style={{ background: '#fff', borderRadius: 8 }} locale={{ emptyText: '当前系统无活跃编辑锁' }} />
      )
    },
    {
      key: 'system',
      label: <span><DashboardOutlined /> 系统资源与基建</span>,
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Row gutter={24}>
            <Col span={8}>
              <Card bordered={false} className="stat-card">
                <Statistic title="CPU 占用率" value={sysStatus?.cpu_pct ?? 0} precision={1} suffix="%" valueStyle={{ color: '#3f8600' }} />
              </Card>
            </Col>
            <Col span={8}>
              <Card bordered={false} className="stat-card">
                <Statistic title="内存 占用率" value={sysStatus?.memory_pct ?? 0} precision={1} suffix="%" valueStyle={{ color: '#cf1322' }} />
              </Card>
            </Col>
            <Col span={8}>
              <Card bordered={false} className="stat-card">
                <Statistic title="AI 探针状态" value={sysStatus?.ai_engine_online ? '在线' : '离线'} valueStyle={{ color: sysStatus?.ai_engine_online ? '#3f8600' : '#cf1322' }} />
              </Card>
            </Col>
          </Row>
          
          <Card title="指挥部高危操作" headStyle={{ color: '#cf1322' }}>
            <Space size="middle">
              <Popconfirm title="这将清理所有失效的临时文件和死信队列，确定？" onConfirm={handleCleanup}>
                <Button danger icon={<DeleteOutlined />}>肃清系统残余缓存</Button>
              </Popconfirm>
              <Button icon={<SyncOutlined />} onClick={fetchData}>刷新实时状态</Button>
              <Button type="primary" ghost icon={<SettingOutlined />}>编辑系统阈值 (TTL)</Button>
            </Space>
          </Card>

          <Descriptions title="基建节点详情" bordered size="small" style={{ background: '#fff' }}>
            <Descriptions.Item label="数据库">{sysStatus?.db_connected ? <Tag color="success">已连接</Tag> : <Tag color="error">断开</Tag>}</Descriptions.Item>
            <Descriptions.Item label="缓存队列 (Redis)">{sysStatus?.redis_connected ? <Tag color="success">已连接</Tag> : <Tag color="error">断开</Tag>}</Descriptions.Item>
            <Descriptions.Item label="Celery Workers">{sysStatus?.celery_workers_active ?? 0} 个活跃实例</Descriptions.Item>
            <Descriptions.Item label="Ollama 路由">{sysStatus?.ai_engine_online ? 'http://10.132.60.133:11434' : '-'}</Descriptions.Item>
          </Descriptions>
        </Space>
      )
    }
  ];

  return (
    <Layout style={{ padding: '24px', background: '#f0f2f5', minHeight: '100%' }}>
      <Title level={3} style={{ color: '#003366', marginBottom: 24 }}>系统中枢设置台 (Control Console)</Title>
      
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab} 
        items={items} 
        type="line" 
        size="large" 
      />

      <Modal
        title={`管理用户: ${editingUser?.username}`}
        open={userModalVisible}
        onOk={() => form.submit()}
        onCancel={() => setUserModalVisible(false)}
      >
        <Form form={form} layout="vertical" onFinish={handleUpdateUser}>
          <Form.Item name="role_level" label="权限等级">
            <Select>
              <Option value={1}>普通职员 (Level 1)</Option>
              <Option value={5}>科室负责人 (Level 5)</Option>
              <Option value={99}>系统管理员 (Level 99)</Option>
            </Select>
          </Form.Item>
          <Form.Item name="is_active" label="账号状态" valuePropName="checked">
            <Select>
              <Option value={true}>正常启用</Option>
              <Option value={false}>停用封禁</Option>
            </Select>
          </Form.Item>
          <Form.Item name="password" label="强制重置密码 (留空则不修改)">
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
};
