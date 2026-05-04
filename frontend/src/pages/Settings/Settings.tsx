import React, { useState, useEffect } from 'react';
import { Layout, Tabs, Card, Table, Tag, Button, Space, Typography, Descriptions, Badge, Modal, Input, message, Alert, Statistic, Row, Col } from 'antd';
import { 
  SettingOutlined, 
  HistoryOutlined, 
  LockOutlined, 
  CodeOutlined, 
  DashboardOutlined,
  SyncOutlined,
  UnlockOutlined,
  SaveOutlined
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import './Settings.css';

const { Title, Text } = Typography;

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState('health');

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Title level={3}><SettingOutlined /> 系统中枢设置</Title>
        <Text type="secondary">全局运行状态监测、审计追溯及 AI 提示词热加载中心</Text>
      </div>

      <Card className="settings-card">
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          tabPosition="left"
          items={[
            { key: 'health', label: <span><DashboardOutlined /> 运行健康度</span>, children: <SystemHealth /> },
            { key: 'audit', label: <span><HistoryOutlined /> 全域审计穿透</span>, children: <AuditLogs /> },
            { key: 'locks', label: <span><LockOutlined /> 核心锁控大盘</span>, children: <LockManager /> },
            { key: 'prompt', label: <span><CodeOutlined /> 提示词中心</span>, children: <PromptEditor /> },
          ]}
        />
      </Card>
    </div>
  );
};

const SystemHealth = () => {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/sys/status');
      setStatus(res.data.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchStatus(); }, []);

  return (
    <div className="tab-pane">
      <Row gutter={16}>
        <Col span={6}>
          <Card><Statistic title="数据库连接" value={status?.db_connected ? '正常' : '异常'} valueStyle={{ color: status?.db_connected ? '#3f8600' : '#cf1322' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="Redis 缓存" value={status?.redis_connected ? '正常' : '异常'} valueStyle={{ color: status?.redis_connected ? '#3f8600' : '#cf1322' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="并行 Worker" value={status?.celery_workers_active || 0} suffix="位" /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="AI 引擎状态" value={status?.ai_engine_online ? '在线' : '离线'} valueStyle={{ color: status?.ai_engine_online ? '#3f8600' : '#cf1322' }} /></Card>
        </Col>
      </Row>
      <Alert 
        message="系统健康提示" 
        description="当前所有核心服务运行正常。SIP 存证指纹生成逻辑已处于热备状态。" 
        type="info" 
        showIcon 
        style={{ marginTop: 24 }}
      />
      <Button icon={<SyncOutlined />} onClick={fetchStatus} loading={loading} style={{ marginTop: 24 }}>刷新探针</Button>
    </div>
  );
};

const AuditLogs = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchAudit = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/sys/audit');
      setData(res.data.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAudit(); }, []);

  const columns = [
    { title: '审计 ID', dataIndex: 'audit_id', key: 'id' },
    { title: '公文 ID', dataIndex: 'doc_id', key: 'doc' },
    { title: '节点', dataIndex: 'node', key: 'node', render: (n: number) => <Tag>{n}</Tag> },
    { title: '操作人', dataIndex: 'operator', key: 'op' },
    { title: '时间', dataIndex: 'time', key: 'time', render: (t: string) => new Date(t).toLocaleString() },
  ];

  return <Table columns={columns} dataSource={data} loading={loading} size="small" />;
};

const LockManager = () => {
  const [locks, setLocks] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchLocks = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/sys/locks');
      setLocks(res.data.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLocks(); }, []);

  const handleForceRelease = (docId: string) => {
    Modal.confirm({
      title: '警告：强制夺锁',
      content: '强制释放锁可能导致正在编辑的用户数据丢失（如未开启容灾保存）。是否继续？',
      okText: '强行夺锁',
      okType: 'danger',
      onOk: async () => {
        await apiClient.delete(`/locks/${docId}`);
        message.success('锁已物理释放，审计已记录');
        fetchLocks();
      }
    });
  };

  const columns = [
    { title: '公文 ID', dataIndex: 'doc_id', key: 'doc' },
    { title: '持锁人', dataIndex: 'username', key: 'user' },
    { title: '剩余时间', dataIndex: 'ttl', key: 'ttl', render: (t: number) => `${t}s` },
    { 
      title: '操作', 
      key: 'action', 
      render: (_: any, record: any) => (
        <Button danger type="text" icon={<UnlockOutlined />} onClick={() => handleForceRelease(record.doc_id)}>强放</Button>
      )
    },
  ];

  return <Table columns={columns} dataSource={locks} loading={loading} pagination={false} size="small" />;
};

const PromptEditor = () => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiClient.get('/sys/prompt').then(res => setContent(res.data.data.content));
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      await apiClient.post('/sys/prompt', { content });
      message.success('提示词已热加载，新对话将立即生效');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="prompt-editor-pane">
      <Alert message="危险操作区" description="修改系统提示词会直接影响 HRAG 问答的严谨性与安全性。请务必保留 {context} 与 {query} 占位符。" type="warning" showIcon style={{ marginBottom: 16 }} />
      <Input.TextArea 
        value={content} 
        onChange={e => setContent(e.target.value)} 
        rows={20} 
        style={{ fontFamily: 'monospace', fontSize: 13 }}
      />
      <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={loading} style={{ marginTop: 16 }}>保存并全量刷新</Button>
    </div>
  );
};