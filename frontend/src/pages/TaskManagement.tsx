import React, { useEffect, useState } from 'react';
import { Layout, Typography, Table, Tag, Button, Space, Progress, message } from 'antd';
import apiClient from '../api/client';
import { SyncOutlined, LoadingOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { Content } = Layout;
const { Title } = Typography;

export const TaskManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState([]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      // 拉取所有异步任务
      const res = await apiClient.get('/tasks/');
      setTasks(res.data);
    } catch (e) {
      message.error('无法获取任务列表');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    const timer = setInterval(fetchTasks, 10000); // 每 10s 自动刷新一次
    return () => clearInterval(timer);
  }, []);

  const columns = [
    {
      title: '任务类型',
      dataIndex: 'task_type',
      key: 'task_type',
      render: (type: string) => {
        const typeMap: any = { 'POLISH': '语义润色', 'FORMAT': '标准排版', 'PARSE': '知识库解析' };
        return <Tag color="blue">{typeMap[type] || type}</Tag>;
      }
    },
    {
      title: '状态',
      dataIndex: 'task_status',
      key: 'task_status',
      render: (status: string) => {
        if (status === 'PROCESSING') return <Tag icon={<LoadingOutlined spin />} color="processing">正在执行</Tag>;
        if (status === 'COMPLETED') return <Tag icon={<CheckCircleOutlined />} color="success">已完成</Tag>;
        if (status === 'FAILED') return <Tag icon={<CloseCircleOutlined />} color="error">失败</Tag>;
        if (status === 'QUEUED') return <Tag icon={<SyncOutlined spin />} color="default">排队中</Tag>;
        return <Tag>{status}</Tag>;
      }
    },
    {
        title: '进度',
        dataIndex: 'progress_pct',
        key: 'progress_pct',
        render: (pct: number) => <Progress percent={pct} size="small" />
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (msg: string) => msg ? <Typography.Text type="danger">{msg}</Typography.Text> : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string) => dayjs(val).format('MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          {record.task_status === 'FAILED' && (
            <Button size="small" onClick={() => handleRetry(record.task_id)}>重试</Button>
          )}
        </Space>
      ),
    },
  ];

  const handleRetry = async (taskId: string) => {
    try {
      await apiClient.post(`/tasks/${taskId}/retry`);
      message.success('已触发重试');
      fetchTasks();
    } catch (e) {
      message.error('重试失败');
    }
  };

  return (
    <Layout style={{ padding: 24, background: '#f0f2f5', minHeight: '100%' }} aria-label="任务管理中心">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ color: '#003366', margin: 0 }}>任务管理中心 (Async Tasks)</Title>
        <Button icon={<SyncOutlined />} onClick={fetchTasks} loading={loading}>手动刷新</Button>
      </div>
      
      <Table 
        columns={columns} 
        dataSource={tasks} 
        rowKey="task_id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        style={{ background: '#fff', borderRadius: 8 }}
      />
    </Layout>
  );
};
