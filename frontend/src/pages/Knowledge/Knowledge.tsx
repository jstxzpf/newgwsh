import React, { useState, useEffect } from 'react';
import { Layout, Tabs, Card, Table, Tag, Button, Space, Typography, Breadcrumb, Modal, Upload, message, Tooltip, Drawer, Form, Select, Input } from 'antd';
import {
  FolderOutlined,
  FileTextOutlined,
  UploadOutlined,
  DeleteOutlined,
  CloudSyncOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
  PlusOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { useAuthStore } from '../../stores/authStore';
import { KBTier, DataSecurityLevel } from '../../types/enums'; // 假设已定义

const { Content, Sider } = Layout;
const { Title, Text } = Typography;

export const Knowledge: React.FC = () => {
  const [activeTier, setActiveTier] = useState<string>('PERSONAL');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadVisible, setUploadVisible] = useState(false);
  const userInfo = useAuthStore(state => state.userInfo);

  const fetchHierarchy = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/kb/hierarchy', { params: { tier: activeTier } });
      setData(res.data.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHierarchy();
  }, [activeTier]);

  const handleDelete = (kbId: number) => {
    Modal.confirm({
      title: '确认删除此资产？',
      content: '警告：目录类型将触发级联软删除，所有子文件及 AI 向量切片将被物理移除。',
      okText: '确认删除',
      okType: 'danger',
      onOk: async () => {
        await apiClient.delete(`/kb/${kbId}`);
        message.success('已移入回收站（软删除）');
        fetchHierarchy();
      }
    });
  };

  const handleReparse = async (kbId: number) => {
    try {
      await apiClient.post(`/kb/${kbId}/reparse`);
      message.success('重新解析任务已派发');
      fetchHierarchy();
    } catch (e: any) {
      message.error(e?.response?.data?.message || '重新解析失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'kb_name',
      key: 'name',
      render: (text: string, record: any) => (
        <Space>
          {record.kb_type === 'DIRECTORY' ? <FolderOutlined style={{ color: '#faad14' }} /> : <FileTextOutlined style={{ color: '#1890ff' }} />}
          <span style={{ fontWeight: 500 }}>{text}</span>
        </Space>
      ),
    },
    {
      title: '密级',
      dataIndex: 'security_level',
      key: 'security',
      render: (level: string) => {
        const config: any = {
          'CORE': { color: 'red', text: '🔒 核心', icon: <LockOutlined /> },
          'IMPORTANT': { color: 'orange', text: '⚠️ 重要', icon: <SafetyCertificateOutlined /> },
          'GENERAL': { color: 'blue', text: '公开', icon: null },
        };
        const item = config[level] || config['GENERAL'];
        return <Tag color={item.color} icon={item.icon}>{item.text}</Tag>;
      },
    },
    {
      title: '解析状态',
      dataIndex: 'parse_status',
      key: 'status',
      render: (status: string) => {
        const colors: any = { 'READY': 'success', 'PARSING': 'processing', 'FAILED': 'error', 'UPLOADED': 'default' };
        return <Badge status={colors[status] || 'default'} text={status} />;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          {record.parse_status === 'FAILED' && (
            <Tooltip title="重新解析">
              <Button type="text" icon={<ReloadOutlined />} onClick={() => handleReparse(record.kb_id)} />
            </Tooltip>
          )}
          <Tooltip title="替换上传">
             <Button type="text" icon={<CloudSyncOutlined />} />
          </Tooltip>
          <Button type="text" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.kb_id)} />
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
           <Title level={3} style={{ margin: 0 }}>统计知识资产库</Title>
           <Breadcrumb items={[{ title: '首页' }, { title: '知识库' }]} style={{ marginTop: 8 }} />
        </div>
        <Space>
           <Button icon={<PlusOutlined />}>新建文件夹</Button>
           <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadVisible(true)}>上传资产</Button>
        </Space>
      </div>

      <Card>
        <Tabs 
          activeKey={activeTier} 
          onChange={setActiveTier}
          items={[
            { key: 'PERSONAL', label: '个人沙箱库' },
            { key: 'DEPT', label: '科室共享库', disabled: (userInfo?.role_level || 0) < 5 },
            { key: 'BASE', label: '全局基础库', disabled: (userInfo?.role_level || 0) < 99 },
            { key: 'EXEMPLAR', label: '参考范文' },
          ]}
        />
        
        <Table 
          columns={columns} 
          dataSource={data} 
          loading={loading}
          rowKey="kb_id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 上传抽屉：强制密级选择 (§三.4) */}
      <UploadDrawer 
        visible={uploadVisible} 
        onClose={() => setUploadVisible(false)} 
        tier={activeTier}
        onSuccess={fetchHierarchy}
      />
    </div>
  );
};

const UploadDrawer: React.FC<{ visible: boolean; onClose: () => void; tier: string; onSuccess: () => void }> = ({ visible, onClose, tier, onSuccess }) => {
  const [form] = Form.useForm();
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (values: any) => {
    setUploading(true);
    const formData = new FormData();
    formData.append('file', values.files[0].originFileObj);
    formData.append('kb_tier', tier);
    formData.append('security_level', values.security_level);
    if (values.parent_id) formData.append('parent_id', values.parent_id);

    try {
      await apiClient.post('/kb/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      message.success('上传成功，解析任务已派发');
      onSuccess();
      onClose();
      form.resetFields();
    } finally {
      setUploading(false);
    }
  };

  return (
    <Drawer title="上传知识资产" width={480} onClose={onClose} open={visible}>
      <Form form={form} layout="vertical" onFinish={handleUpload} initialValues={{ security_level: 'GENERAL' }}>
        <Form.Item name="files" label="文件" valuePropName="fileList" getValueFromEvent={(e: any) => Array.isArray(e) ? e : e?.fileList} rules={[{ required: true }]}>
          <Upload.Dragger beforeUpload={() => false} maxCount={1}>
            <p className="ant-upload-drag-icon"><UploadOutlined /></p>
            <p className="ant-upload-text">点击或拖拽文件至此处上传</p>
            <p className="ant-upload-hint">支持 PDF, Word, Excel, Markdown 格式</p>
          </Upload.Dragger>
        </Form.Item>

        <Form.Item name="security_level" label="安全等级 (铁律：核心资产不参与RAG)" rules={[{ required: true }]}>
          <Select>
            <Select.Option value="GENERAL">一般公开数据</Select.Option>
            <Select.Option value="IMPORTANT">重要统计数据 (强制水印召回)</Select.Option>
            <Select.Option value="CORE">🔒 核心涉密数据 (禁止召回)</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={uploading}>开始上传</Button>
        </Form.Item>
      </Form>
    </Drawer>
  );
};

import { Badge } from 'antd';