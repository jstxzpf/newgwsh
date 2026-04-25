import React, { useState, useEffect } from 'react';
import { Table, Button, Upload, Tag, message, Layout, Typography, Tabs } from 'antd';
import { UploadOutlined, FileTextOutlined, LockOutlined } from '@ant-design/icons';
import apiClient from '../api/client';
import { useTaskWatcher } from '../hooks/useTaskWatcher';
import { useAuthStore } from '../store/useAuthStore';

const { Header, Content } = Layout;
const { Title } = Typography;

export const KnowledgeBase: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const { watchTask } = useTaskWatcher();
  const userInfo = useAuthStore(state => state.userInfo);

  const fetchHierarchy = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/kb/hierarchy');
      setData(res.data.data);
    } catch (e) {
      message.error("获取知识库失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHierarchy();
  }, []);

  const handleUpload = async (options: any, tier: string) => {
    const { file, onSuccess, onError } = options;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('kb_tier', tier);
    formData.append('security_level', 'GENERAL'); // 默认一般

    try {
      const res = await apiClient.post('/kb/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      message.success(`${file.name} 上传成功，开始解析`);
      onSuccess(res.data);
      
      watchTask(res.data.task_id, () => {
        message.success(`${file.name} 解析完成`);
        fetchHierarchy();
      });
      fetchHierarchy();
    } catch (err) {
      onError(err);
      message.error(`${file.name} 上传失败`);
    }
  };

  const columns = [
    {
      title: '资产名称',
      dataIndex: 'kb_name',
      key: 'kb_name',
      render: (text: string) => <div style={{ display: 'flex', alignItems: 'center' }}><FileTextOutlined style={{ marginRight: 8, color: '#1677ff' }}/> <span style={{ fontWeight: 500 }}>{text}</span></div>
    },
    {
      title: '层级',
      dataIndex: 'kb_tier',
      key: 'kb_tier',
      render: (tier: string) => (
        <Tag color={tier === 'BASE' ? 'blue' : tier === 'DEPT' ? 'purple' : 'default'}>{tier}</Tag>
      )
    },
    {
      title: '涉密等级',
      dataIndex: 'security_level',
      key: 'security_level',
      render: (level: string) => (
        <Tag color={level === 'CORE' ? 'red' : level === 'IMPORTANT' ? 'orange' : 'green'}>{level}</Tag>
      )
    },
    {
      title: '解析状态',
      dataIndex: 'parse_status',
      key: 'parse_status',
      render: (status: string) => {
        let color = 'default';
        if (status === 'READY') color = 'success';
        if (status === 'PARSING') color = 'processing';
        if (status === 'FAILED') color = 'error';
        return <Tag color={color}>{status}</Tag>;
      }
    },
    {
      title: '操作',
      key: 'action',
      render: () => <Button type="link" size="small" danger>软删除</Button>
    }
  ];

  // 按类型过滤数据
  const personalData = data.filter(d => d.kb_tier === 'PERSONAL');
  const deptData = data.filter(d => d.kb_tier === 'DEPT');
  const baseData = data.filter(d => d.kb_tier === 'BASE');

  const renderTabContent = (tier: string, tierData: any[], canUpload: boolean) => (
    <div style={{ background: '#fff', padding: '24px', borderRadius: '4px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
        <Title level={5} style={{ margin: 0, color: '#555' }}>
          共 {tierData.length} 份可用台账资源
        </Title>
        <Upload customRequest={(opt) => handleUpload(opt, tier)} showUploadList={false} disabled={!canUpload}>
          <Button 
            type="primary" 
            icon={canUpload ? <UploadOutlined /> : <LockOutlined />} 
            disabled={!canUpload}
            style={{ backgroundColor: canUpload ? '#003366' : undefined }}
          >
            {canUpload ? '上传新台账' : '暂无上传权限'}
          </Button>
        </Upload>
      </div>
      <Table columns={columns} dataSource={tierData} rowKey="kb_id" loading={loading} pagination={{ pageSize: 10 }} />
    </div>
  );

  // 权限控制：科长(>=5)可传DEPT，管理员(>=99)可传BASE
  const role = userInfo?.roleLevel || 1;

  const tabItems = [
    { key: 'PERSONAL', label: '个人沙箱库', children: renderTabContent('PERSONAL', personalData, true) },
    { key: 'DEPT', label: '科室共享库', children: renderTabContent('DEPT', deptData, role >= 5) },
    { key: 'BASE', label: '全局基础库', children: renderTabContent('BASE', baseData, role >= 99) }
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#ffffff', borderBottom: '1px solid #f0f0f0', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <h2 style={{ color: '#003366', margin: 0, fontSize: '18px', fontWeight: 'bold' }}>统计知识资产库 (KB Admin)</h2>
      </Header>
      <Content style={{ padding: '24px', background: 'var(--bg-workspace)' }}>
        <Tabs defaultActiveKey="PERSONAL" items={tabItems} type="card" size="large" />
      </Content>
    </Layout>
  );
};
