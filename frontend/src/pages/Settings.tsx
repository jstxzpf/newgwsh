import React, { useState, useEffect } from 'react';
import { Tabs, Table, Tag, Button, Form, Switch, InputNumber, Row, Col, Statistic, List, Typography, theme, message, Space, Modal, Input } from 'antd';
import {
  UserOutlined,
  GlobalOutlined,
  LockOutlined,
  CheckCircleOutlined,
  SettingOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { sysService, authService, SystemStatus } from '../api/services';

const { Title, Text } = Typography;

// [P1] harden: 定义严格数据接口
interface SystemUser {
  key: string;
  username: string;
  full_name: string;
  dept: string;
  role: string;
  active: boolean;
}

const Settings: React.FC = () => {
  const { token } = theme.useToken();
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<SystemStatus | null>(null);
  
  const [prompts, setPrompts] = useState<{filename: string, path: string}[]>([]);
  const [editPromptVisible, setEditPromptVisible] = useState(false);
  const [currentPrompt, setCurrentPrompt] = useState<{filename: string, content: string} | null>(null);

  const fetchHealth = async () => {
    try {
      // [P0] harden: 由于拦截器已解构 res.data，直接使用 res
      const res = await sysService.getStatus();
      setHealth(res);
    } catch (error) {
      console.error('Failed to fetch health status');
    }
  };

  const fetchPrompts = async () => {
    try {
      const res = await sysService.getPrompts();
      setPrompts(res);
    } catch (error) {
      console.error('Failed to fetch prompts', error);
    }
  };

  const handleEditPrompt = async (filename: string) => {
    try {
      const res = await sysService.getPrompt(filename);
      setCurrentPrompt(res);
      setEditPromptVisible(true);
    } catch (error) {
      message.error('无法读取提示词内容');
    }
  };

  const handleSavePrompt = async () => {
    if (!currentPrompt) return;
    try {
      await sysService.updatePrompt(currentPrompt.filename, currentPrompt.content);
      message.success('提示词已保存并热加载');
      setEditPromptVisible(false);
    } catch (error) {
      message.error('保存失败');
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchPrompts();
  }, []);

  const tabItems = [
    {
      key: 'users',
      label: <span><UserOutlined /> 用户管理</span>,
      children: (
        <Table
          size="middle"
          columns={[
            { title: '工号', dataIndex: 'username', key: 'username' },
            { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
            { title: '科室', dataIndex: 'dept', key: 'dept' },
            { title: '角色', dataIndex: 'role', key: 'role', render: (r: string) => <Tag color="blue">{r}</Tag> },
            { title: '状态', dataIndex: 'active', key: 'active', render: (a: boolean) => <Switch checked={a} size="small" /> },
            { title: '操作', key: 'action', render: () => <Button type="link" size="small">重置密码</Button> },
          ]}
          dataSource={[
            { key: '1', username: 'admin', full_name: '系统管理员', dept: '办公室', role: '管理员', active: true },
          ]}
        />
      ),
    },
    {
      key: 'config',
      label: <span><SettingOutlined /> 系统参数</span>,
      children: (
        <Form layout="vertical" initialValues={{ lock_ttl: 180, heartbeat: 90, ollama_timeout: 120 }} style={{ maxWidth: 800 }}>
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
          <Button type="primary">保存配置修改</Button>
        </Form>
      ),
    },
    {
      key: 'health',
      label: <span><GlobalOutlined /> 健康监控</span>,
      children: (
        <div style={{ padding: '8px 0' }}>
          <Row gutter={[16, 16]}>
            <Col span={6}>
              <div style={{ padding: token.paddingMD, background: token.colorFillQuaternary, borderRadius: token.borderRadiusSM }}>
                <Statistic 
                  title="数据库状态" 
                  value={health?.db_connected ? '在线' : '离线'} 
                  valueStyle={{ color: health?.db_connected ? token.colorSuccess : token.colorError }} 
                  prefix={<CheckCircleOutlined />} 
                />
              </div>
            </Col>
            <Col span={6}>
              <div style={{ padding: token.paddingMD, background: token.colorFillQuaternary, borderRadius: token.borderRadiusSM }}>
                <Statistic 
                  title="Redis 状态" 
                  value={health?.redis_connected ? '在线' : '离线'} 
                  valueStyle={{ color: health?.redis_connected ? token.colorSuccess : token.colorError }} 
                  prefix={<CheckCircleOutlined />} 
                />
              </div>
            </Col>
            <Col span={6}>
              <div style={{ padding: token.paddingMD, background: token.colorFillQuaternary, borderRadius: token.borderRadiusSM }}>
                <Statistic 
                  title="AI 联机引擎" 
                  value={health?.ai_engine_online ? '正常' : '异常'} 
                  valueStyle={{ color: health?.ai_engine_online ? token.colorSuccess : token.colorError }} 
                  prefix={<SyncOutlined spin={health?.ai_engine_online} />} 
                />
              </div>
            </Col>
            <Col span={6}>
              <div style={{ padding: token.paddingMD, background: token.colorFillQuaternary, borderRadius: token.borderRadiusSM }}>
                <Statistic 
                  title="CPU 资源占用" 
                  value={health?.cpu_usage_pct || 15} 
                  suffix="%" 
                  valueStyle={{ color: (health?.cpu_usage_pct || 0) > 80 ? token.colorError : token.colorInfo }}
                />
              </div>
            </Col>
          </Row>
        </div>
      ),
    },
    {
      key: 'prompts',
      label: <span><FileTextOutlined /> 提示词管理</span>,
      children: (
        <List
          dataSource={prompts}
          renderItem={(item: {filename: string, path: string}) => (
            <List.Item actions={[<Button type="link" onClick={() => handleEditPrompt(item.filename)}>在线编辑</Button>]}>
              <List.Item.Meta 
                avatar={<FileTextOutlined style={{ fontSize: 24, color: token.colorPrimary }} />}
                title={item.filename} 
                description={`核心业务逻辑支撑文件 | 路径: ${item.path}`} 
              />
            </List.Item>
          )}
        />
      ),
    },
    {
      key: 'locks',
      label: <span><LockOutlined /> 锁监控</span>,
      children: (
        <Table
          size="middle"
          columns={[
            { title: '文档标题', dataIndex: 'title', key: 'title' },
            { title: '持有者', dataIndex: 'owner', key: 'owner' },
            { title: '剩余有效时间', dataIndex: 'ttl', key: 'ttl', render: (t: number) => <Tag color="orange">{t}s</Tag> },
            { title: '管理操作', key: 'action', render: () => <Button danger size="small" type="text">强制释放</Button> },
          ]}
          dataSource={[]}
          locale={{ emptyText: '当前系统中无活跃编辑锁' }}
        />
      ),
    },
  ];

  return (
    // [P0] layout: 引入“权威长卷”容器
    <div style={{ padding: 40, backgroundColor: token.colorBgLayout, minHeight: '100%' }}>
      <div style={{ 
        maxWidth: 1200, 
        margin: '0 auto', 
        backgroundColor: token.colorBgContainer,
        borderRadius: token.borderRadiusSM,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        padding: token.paddingLG
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: token.marginLG }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <Space><SafetyCertificateOutlined /> 系统中枢设置</Space>
            </Title>
            <Text type="secondary">配置全局参数与资产安全策略，监控系统核心引擎状态</Text>
          </div>
          <Button icon={<SyncOutlined />} onClick={fetchHealth}>刷新状态</Button>
        </div>

        {/* [P1] layout: 优化 Tabs 样式，使其更符合严肃风格 */}
        <Tabs 
          tabPosition="left" 
          items={tabItems} 
          style={{ minHeight: 400 }}
          tabBarStyle={{ borderRight: `1px solid ${token.colorBorderSecondary}`, width: 160 }}
        />
      </div>

      <Modal
        title={`编辑提示词: ${currentPrompt?.filename}`}
        open={editPromptVisible}
        onOk={handleSavePrompt}
        onCancel={() => setEditPromptVisible(false)}
        width={800}
        okText="保存并热加载"
      >
        <Input.TextArea
          rows={15}
          value={currentPrompt?.content}
          onChange={(e) => setCurrentPrompt(prev => prev ? { ...prev, content: e.target.value } : null)}
          style={{ fontFamily: 'monospace' }}
        />
      </Modal>
    </div>
  );
};

export default Settings;
