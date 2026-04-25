import React, { useState, useEffect } from 'react';
import { Table, Button, Upload, Tag, message, Layout, Typography } from 'antd';
import { UploadOutlined, FileTextOutlined } from '@ant-design/icons';
import apiClient from '../api/client';
import { useTaskWatcher } from '../hooks/useTaskWatcher';

const { Header, Content } = Layout;
const { Title } = Typography;

export const KnowledgeBase: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const { watchTask } = useTaskWatcher();

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

  const handleUpload = async (options: any) => {
    const { file, onSuccess, onError } = options;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('kb_tier', 'PERSONAL');
    formData.append('security_level', 'GENERAL');

    try {
      const res = await apiClient.post('/kb/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      message.success(`${file.name} 上传成功，开始解析`);
      onSuccess(res.data);
      
      // 监听解析任务
      watchTask(res.data.task_id, () => {
        message.success(`${file.name} 解析完成`);
        fetchHierarchy();
      });
      
      // 先刷新列表展示 PARSING 状态
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
      render: (text: string) => <><FileTextOutlined style={{ marginRight: 8 }}/>{text}</>
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
    }
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#003366', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <h2 style={{ color: '#fff', margin: 0, fontSize: '18px' }}>统计知识资产库 (KB Admin)</h2>
      </Header>
      <Content style={{ padding: '24px', background: 'var(--bg-workspace)' }}>
        <div style={{ background: '#fff', padding: '24px', borderRadius: '4px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
            <Title level={4} style={{ margin: 0 }}>个人沙箱库</Title>
            <Upload customRequest={handleUpload} showUploadList={false}>
              <Button type="primary" icon={<UploadOutlined />} style={{ backgroundColor: '#003366' }}>
                上传新台账
              </Button>
            </Upload>
          </div>
          <Table 
            columns={columns} 
            dataSource={data} 
            rowKey="kb_id" 
            loading={loading}
            pagination={false}
          />
        </div>
      </Content>
    </Layout>
  );
};
