import React, { useState, useEffect } from 'react';
import { Table, Button, Upload, Tag, message, Layout, Typography, Tabs, Popconfirm } from 'antd';
import { UploadOutlined, FileTextOutlined, LockOutlined, DeleteOutlined } from '@ant-design/icons';
import apiClient from '../api/client';
import { useTaskWatcher } from '../hooks/useTaskWatcher';
import { useAuthStore } from '../store/useAuthStore';
import { appConfig } from '../config';

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
      // 后端直接返回的是 roots 数组，而非 { data: [...] }
      const rawData = Array.isArray(res.data) ? res.data : [];
      
      // 深度巡检发现：Table 是按扁平列表展示的，需要将树形结构递归平铺
      const flattenData: any[] = [];
      const flatten = (nodes: any[]) => {
        nodes.forEach(node => {
          flattenData.push(node);
          if (node.children && node.children.length > 0) {
            flatten(node.children);
          }
        });
      };
      flatten(rawData);
      setData(flattenData);
    } catch (e) {
      message.error("获取知识库失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHierarchy();
  }, []);

  const handleDelete = async (kbId: number) => {
      try {
          await apiClient.delete(`/kb/${kbId}`);
          message.success('资产已移入回收站');
          fetchHierarchy();
      } catch (err) {
          message.error('删除失败，权限不足');
      }
  };

  const handleUpload = async (options: any, tier: string) => {
    const { file, onSuccess, onError } = options;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('kb_tier', tier);
    formData.append('security_level', 'GENERAL'); 

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
      render: (text: string, record: any) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {record.kb_type === 'DIRECTORY' ? 
            <FileTextOutlined style={{ marginRight: 8, color: '#faad14' }}/> : 
            <FileTextOutlined style={{ marginRight: 8, color: '#1677ff' }}/>
          } 
          <span style={{ fontWeight: 500 }}>{text}</span>
        </div>
      )
    },
    {
      title: '类型',
      dataIndex: 'kb_type',
      key: 'kb_type',
      render: (type: string) => (
        <Tag color={type === 'DIRECTORY' ? 'orange' : 'blue'}>{type === 'DIRECTORY' ? '目录' : '文件'}</Tag>
      )
    },
    {
      title: '层级',
      dataIndex: 'kb_tier',
      key: 'kb_tier',
      render: (tier: string) => (
        <Tag color={tier === 'BASE' ? 'blue' : tier === 'DEPT' ? 'cyan' : 'default'}>{tier}</Tag>
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
      render: (status: string, record: any) => {
        if (record.kb_type === 'DIRECTORY') return '-';
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
      render: (_: any, record: any) => (
        <Popconfirm title="确定要软删除此资产吗？" onConfirm={() => handleDelete(record.kb_id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>软删除</Button>
        </Popconfirm>
      )
    }
  ];

  const personalData = (data || []).filter(d => d.kb_tier === 'PERSONAL');
  const deptData = (data || []).filter(d => d.kb_tier === 'DEPT');
  const baseData = (data || []).filter(d => d.kb_tier === 'BASE');

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
      <Table columns={columns} dataSource={tierData} rowKey="kb_id" loading={loading} pagination={{ pageSize: appConfig.knowledgePageSize }} />
    </div>
  );

  const role = userInfo?.roleLevel || 1;

  const tabItems = [
    { key: 'PERSONAL', label: '个人沙箱库', children: renderTabContent('PERSONAL', personalData, true) },
    { key: 'DEPT', label: '科室共享库', children: renderTabContent('DEPT', deptData, role >= 5) },
    { key: 'BASE', label: '全局基础库', children: renderTabContent('BASE', baseData, role >= 99) }
  ];

  return (
    <Layout style={{ minHeight: '100vh' }} aria-label="知识库管理容器">
      <Header style={{ background: '#ffffff', borderBottom: '1px solid #f0f0f0', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <h2 style={{ color: '#003366', margin: 0, fontSize: '18px', fontWeight: 'bold' }}>统计知识资产库 (KB Admin)</h2>
      </Header>
      <Content style={{ padding: '24px', background: 'var(--bg-workspace)' }}>
        <Tabs defaultActiveKey="PERSONAL" items={tabItems} type="card" size="large" />
      </Content>
    </Layout>
  );
};
