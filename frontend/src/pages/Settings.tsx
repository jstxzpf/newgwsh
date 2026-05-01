import React from 'react';
import { Card, Tabs, Table, Tag, Button, Form, Switch, InputNumber, Row, Col, Statistic, List } from 'antd';
import {
  UserOutlined,
  GlobalOutlined,
  LockOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  FileTextOutlined,
} from '@ant-design/icons';

const Settings: React.FC = () => {
  const tabItems = [
    {
      key: 'users',
      label: <span><UserOutlined />用户管理</span>,
      children: (
        <Table
          columns={[
            { title: '工号', dataIndex: 'username', key: 'username' },
            { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
            { title: '科室', dataIndex: 'dept', key: 'dept' },
            { title: '角色', dataIndex: 'role', key: 'role', render: (r: string) => <Tag color="blue">{r}</Tag> },
            { title: '状态', dataIndex: 'active', key: 'active', render: (a: boolean) => <Switch checked={a} /> },
            { title: '操作', key: 'action', render: () => <Button type="link">重置密码</Button> },
          ]}
          dataSource={[
            { key: '1', username: 'admin', full_name: '系统管理员', dept: '办公室', role: '管理员', active: true },
          ]}
        />
      ),
    },
    {
      key: 'config',
      label: <span><SettingOutlined />系统参数</span>,
      children: (
        <Form layout="vertical" initialValues={{ lock_ttl: 180, heartbeat: 90, ollama_timeout: 120 }}>
          <Row gutter={24}>
            <Col span={8}>
              <Form.Item label="编辑锁 TTL (秒)" name="lock_ttl">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="心跳间隔 (秒)" name="heartbeat">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Ollama HTTP 超时 (秒)" name="ollama_timeout">
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Button type="primary">保存配置</Button>
        </Form>
      ),
    },
    {
      key: 'health',
      label: <span><GlobalOutlined />健康监控</span>,
      children: (
        <Row gutter={16}>
          <Col span={6}><Card><Statistic title="数据库" value="在线" valueStyle={{ color: '#3f8600' }} prefix={<CheckCircleOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="Redis" value="在线" valueStyle={{ color: '#3f8600' }} prefix={<CheckCircleOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="AI 引擎" value="在线" valueStyle={{ color: '#3f8600' }} prefix={<CheckCircleOutlined />} /></Card></Col>
          <Col span={6}><Card><Statistic title="CPU 使用率" value={15} suffix="%" /></Card></Col>
        </Row>
      ),
    },
    {
      key: 'prompts',
      label: <span><FileTextOutlined />提示词管理</span>,
      children: (
        <List
          dataSource={['system_chat.txt', 'system_polish.txt']}
          renderItem={(item: string) => (
            <List.Item actions={[<Button type="link">编辑</Button>]}>
              <List.Item.Meta title={item} description="最后更新: 2026-04-30 10:00" />
            </List.Item>
          )}
        />
      ),
    },
    {
      key: 'locks',
      label: <span><LockOutlined />锁监控</span>,
      children: (
        <Table
          columns={[
            { title: '文档标题', dataIndex: 'title', key: 'title' },
            { title: '持有者', dataIndex: 'owner', key: 'owner' },
            { title: '剩余 TTL', dataIndex: 'ttl', key: 'ttl', render: (t: number) => `${t}s` },
            { title: '操作', key: 'action', render: () => <Button danger size="small">强制释放</Button> },
          ]}
          dataSource={[]}
          locale={{ emptyText: '当前无活跃编辑锁' }}
        />
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title="系统中枢设置">
        <Tabs tabPosition="left" items={tabItems} />
      </Card>
    </div>
  );
};

export default Settings;
