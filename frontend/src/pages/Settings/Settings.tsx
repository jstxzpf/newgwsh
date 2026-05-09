import React, { useState, useEffect } from 'react';
import { Tabs, Card, Table, Tag, Button, Space, Typography, Modal, Input, message, Alert, Statistic, Row, Col } from 'antd';
import {
  SettingOutlined,
  HistoryOutlined,
  LockOutlined,
  CodeOutlined,
  DashboardOutlined,
  SyncOutlined,
  UnlockOutlined,
  SaveOutlined,
  FileTextOutlined,
  EditOutlined
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
            { key: 'doctypes', label: <span><FileTextOutlined /> 文种管理</span>, children: <DocTypeManager /> },
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

const DocTypeManager = () => {
  const [docTypes, setDocTypes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [editVisible, setEditVisible] = useState(false);
  const [editingType, setEditingType] = useState<any>(null);
  const [jsonText, setJsonText] = useState('');

  const fetchDocTypes = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/sys/doc-types');
      setDocTypes(res.data.data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDocTypes(); }, []);

  const handleEdit = (dt: any) => {
    setEditingType(dt);
    setJsonText(JSON.stringify(dt.layout_rules || {}, null, 2));
    setEditVisible(true);
  };

  const handleSave = async () => {
    try {
      const parsed = JSON.parse(jsonText);
      await apiClient.put(`/sys/doc-types/${editingType.type_id}`, {
        type_name: editingType.type_name,
        layout_rules: parsed,
      });
      message.success('文种模板已保存');
      setEditVisible(false);
      fetchDocTypes();
    } catch (e: any) {
      if (e instanceof SyntaxError) {
        message.error('JSON 格式错误，请检查语法');
      } else {
        message.error('保存失败: ' + (e.response?.data?.message || e.message));
      }
    }
  };

  const handleToggle = async (dt: any) => {
    try {
      await apiClient.put(`/sys/doc-types/${dt.type_id}`, { is_active: !dt.is_active });
      message.success(dt.is_active ? '已停用' : '已启用');
      fetchDocTypes();
    } catch (e: any) {
      message.error('操作失败');
    }
  };

  const columns = [
    { title: '编码', dataIndex: 'type_code', key: 'code' },
    { title: '文种名称', dataIndex: 'type_name', key: 'name' },
    { title: '状态', dataIndex: 'is_active', key: 'active', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '停用'}</Tag> },
    {
      title: '模板节数',
      key: 'sections',
      render: (_: any, r: any) => {
        const tpl = r.layout_rules?.template;
        return tpl ? `${tpl.length} 节` : '基础';
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, r: any) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(r)}>编辑模板</Button>
          <Button type="link" danger={r.is_active} onClick={() => handleToggle(r)}>
            {r.is_active ? '停用' : '启用'}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        管理公文文种的国标排版模板。编辑 layout_rules 中的 template 数组可调整 .docx 输出结构。{'"'}通用文档{'"'}文种无需模板，仅执行基础排版。
      </Text>
      <Table columns={columns} dataSource={docTypes} loading={loading} rowKey="type_id" size="small" pagination={false} />
      <Modal
        title={`编辑排版模板 — ${editingType?.type_name || ''}`}
        open={editVisible}
        onOk={handleSave}
        onCancel={() => setEditVisible(false)}
        width={800}
        okText="保存模板"
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          编辑 JSON 定义。template 数组每节支持 type: red_header | paragraph | separator | body | ending
        </Text>
        <Input.TextArea
          value={jsonText}
          onChange={e => setJsonText(e.target.value)}
          rows={22}
          style={{ fontFamily: 'monospace', fontSize: 13 }}
        />
      </Modal>
    </div>
  );
};