import React from 'react';
import { Table, Tag, Space, Button, Card } from 'antd';
import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const Approvals: React.FC = () => {
  const navigate = useNavigate();

  const columns = [
    { title: '公文标题', dataIndex: 'title', key: 'title' },
    { title: '科室', dataIndex: 'dept', key: 'dept' },
    { title: '起草人', dataIndex: 'creator', key: 'creator' },
    { title: '提交时间', dataIndex: 'submittedAt', key: 'submittedAt' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: () => <Tag color="blue">待签批</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/workspace/${record.key}`)}>审阅</Button>
          <Button type="link" icon={<CheckOutlined />} style={{ color: '#52c41a' }}>批准</Button>
          <Button type="link" danger icon={<CloseOutlined />}>驳回</Button>
        </Space>
      ),
    },
  ];

  const data = [
    { key: '2', title: '泰兴调查队安全生产工作通知', dept: '办公室', creator: '系统管理员', submittedAt: '2026-05-01 10:30' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title="科长签批管控台">
        <Table columns={columns} dataSource={data} />
      </Card>
    </div>
  );
};

export default Approvals;
