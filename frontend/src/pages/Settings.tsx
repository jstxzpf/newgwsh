import React, { useEffect, useState } from 'react';
import { Layout, Typography, Tabs, Table, Card, Button, message, Tag, Space, Form, InputNumber } from 'antd';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';

const { Title } = Typography;
const { TabPane } = Tabs;

export const Settings: React.FC = () => {
  const userInfo = useAuthStore(state => state.userInfo);
  const [userList, setUserList] = useState([]);
  const [locks, setLocks] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [infraConfig, setInfraConfig] = useState({ lock_ttl: 180, sse_retries: 3 });

  const fetchUsers = async () => {
    try {
      const res = await apiClient.get('/users/');
      setUserList(res.data);
    } catch (e) { message.error('拉取用户矩阵失败'); }
  };

  const fetchLocks = async () => {
    try {
      const res = await apiClient.get('/locks/active');
      setLocks(res.data);
    } catch (e) { /* 后端若未实现则跳过 */ }
  };

  const fetchAudit = async () => {
      try {
          const res = await apiClient.get('/audit/');
          setAuditLogs(res.data.data);
      } catch (e) { message.error('无法拉取审计日志'); }
  };

  useEffect(() => {
    if ((userInfo?.roleLevel ?? 0) >= 99) {
      fetchUsers();
      fetchLocks();
      fetchAudit();
    }
  }, [userInfo]);

  const handleUpdateInfra = async (values: any) => {
    try {
        await apiClient.put('/sys/config', values);
        message.success('系统动态配置已刷新');
    } catch (e) {
        message.error('配置更新失败');
    }
  };

  const userColumns = [
    { title: '工号', dataIndex: 'user_id', key: 'user_id' },
    { title: '姓名', dataIndex: 'username', key: 'username' },
    { title: '科室', dataIndex: 'dept_id', key: 'dept_id', render: (id: number) => `Dept ID: ${id}` },
    { title: '权限等级', dataIndex: 'role_level', key: 'role_level', render: (lvl: number) => <Tag>{lvl}</Tag> },
    { title: '状态', dataIndex: 'is_active', key: 'is_active', render: (active: boolean) => active ? <Tag color="green">激活</Tag> : <Tag color="red">禁用</Tag> }
  ];

  if (!userInfo || (userInfo.roleLevel ?? 0) < 99) {
      return (
          <Layout style={{ padding: 48, textAlign: 'center' }}>
              <Title level={4} type="danger">权限不足：系统中枢设置台仅对系统管理员开放。</Title>
          </Layout>
      );
  }

  return (
    <Layout style={{ padding: 24, background: '#f0f2f5', minHeight: '100%' }} aria-label="设置中枢容器">
      <Title level={3} style={{ color: '#003366' }}>系统中枢设置台 (System Settings)</Title>
      
      <Tabs defaultActiveKey="1" style={{ background: '#fff', padding: 24, borderRadius: 8 }}>
        <TabPane tab="用户矩阵管理" key="1">
          <Table dataSource={userList} columns={userColumns} rowKey="user_id" pagination={{ pageSize: 10 }} />
        </TabPane>
        
        <TabPane tab="安全审计溯源" key="2">
          <Table 
            dataSource={auditLogs} 
            rowKey="id"
            columns={[
                { title: '时间', dataIndex: 'action_timestamp', key: 'at' },
                { title: '公文ID', dataIndex: 'doc_id', key: 'doc' },
                { title: '行为', dataIndex: 'node', key: 'node' },
                { title: '详情', dataIndex: 'payload', key: 'payload', render: (p: any) => JSON.stringify(p) }
            ]}
          />
        </TabPane>

        <TabPane tab="强控制悲观锁监控" key="3">
          <Card size="small" title="Redis 活跃编辑锁大盘">
            <Table 
                dataSource={locks}
                columns={[
                    { title: '资源Key', dataIndex: 'key', key: 'key' },
                    { title: '持有者', dataIndex: 'owner', key: 'owner' },
                    { title: '过期时间', dataIndex: 'expires', key: 'expires' },
                    { title: '操作', key: 'op', render: () => <Button danger size="small">强制斩断</Button> }
                ]}
                locale={{ emptyText: '当前集群无活跃死锁' }}
            />
          </Card>
        </TabPane>

        <TabPane tab="系统基建配置" key="4">
            <Card title="全局基建动态嗅探控制">
                <Form 
                    layout="vertical" 
                    initialValues={infraConfig}
                    onFinish={handleUpdateInfra}
                    style={{ maxWidth: '400px' }}
                >
                    <Form.Item label="编辑锁 TTL (秒)" name="lock_ttl">
                        <InputNumber style={{ width: '100%' }} min={60} max={3600} />
                    </Form.Item>
                    <Form.Item label="SSE 最大重试次数" name="sse_retries">
                        <InputNumber style={{ width: '100%' }} min={1} max={10} />
                    </Form.Item>
                    <Form.Item>
                        <Button type="primary" htmlType="submit">保存并刷新配置</Button>
                    </Form.Item>
                </Form>
                <div style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
                    <Button onClick={() => apiClient.post('/sys/cleanup-cache').then(() => message.success('清理任务已触发'))}>
                        立即触发全局缓存清理 (Temp Files & Redis)
                    </Button>
                </div>
            </Card>
        </TabPane>
      </Tabs>
    </Layout>
  );
};
