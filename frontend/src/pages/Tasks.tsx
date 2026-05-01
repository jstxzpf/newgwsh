import React from 'react';
import { Table, Tag, Space, Button, Progress, Card } from 'antd';
import { ReloadOutlined, StopOutlined, EyeOutlined } from '@ant-design/icons';

const Tasks: React.FC = () => {
  const columns = [
    { title: '任务 ID', dataIndex: 'id', key: 'id' },
    { title: '类型', dataIndex: 'type', key: 'type', render: (text: string) => <Tag color="blue">{text}</Tag> },
    {
      title: '当前进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (percent: number, record: any) => (
        <Progress percent={percent} status={record.status === 'FAILED' ? 'exception' : 'active'} size="small" />
      ),
    },
    { title: '状态', dataIndex: 'status', key: 'status', render: (text: string) => {
      let color = 'processing';
      if (text === 'COMPLETED') color = 'success';
      if (text === 'FAILED') color = 'error';
      return <Tag color={color}>{text}</Tag>;
    }},
    { title: '发起人', dataIndex: 'creator', key: 'creator' },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          {record.status === 'FAILED' && <Button type="link" icon={<ReloadOutlined />}>重试</Button>}
          <Button type="link" icon={<EyeOutlined />}>日志</Button>
          <Button type="link" danger icon={<StopOutlined />}>终止</Button>
        </Space>
      ),
    },
  ];

  const data = [
    { key: '1', id: 'POL-782', type: 'AI 润色', progress: 100, status: 'COMPLETED', creator: '系统管理员', createdAt: '2026-05-01 14:10' },
    { key: '2', id: 'FOR-901', type: '国标排版', progress: 45, status: 'PROCESSING', creator: '系统管理员', createdAt: '2026-05-01 15:00' },
    { key: '3', id: 'PAR-442', type: '文件解析', progress: 80, status: 'FAILED', creator: '系统管理员', createdAt: '2026-05-01 12:00' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title="异步任务中心">
        <Table columns={columns} dataSource={data} />
      </Card>
    </div>
  );
};

export default Tasks;
