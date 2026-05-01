import React from 'react';
import { Table, Tag, Space, Button, Input, Card, Modal, Select } from 'antd';
import { SearchOutlined, PlusOutlined, EditOutlined, DownloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Option } = Select;

const DocumentList: React.FC = () => {
  const navigate = useNavigate();

  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title', render: (text: string, record: any) => <a onClick={() => navigate(`/workspace/${record.key}`)}>{text}</a> },
    { title: '文种', dataIndex: 'type', key: 'type', render: (text: string) => <Tag color="blue">{text}</Tag> },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'gold';
        if (status === '已通过') color = 'green';
        if (status === '审批中') color = 'blue';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    { title: '起草人', dataIndex: 'creator', key: 'creator' },
    { title: '最后更新', dataIndex: 'updatedAt', key: 'updatedAt' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button type="link" icon={<EditOutlined />} onClick={() => navigate(`/workspace/${record.key}`)}>查看/编辑</Button>
          {record.status === '已通过' && <Button type="link" icon={<DownloadOutlined />}>下载</Button>}
          <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
        </Space>
      ),
    },
  ];

  const data = [
    { key: '1', title: '关于2024年一季度数据的分析报告', type: '调研分析', status: '起草中', creator: '系统管理员', updatedAt: '2026-05-01 14:20' },
    { key: '2', title: '泰兴调查队安全生产工作通知', type: '通知', status: '审批中', creator: '系统管理员', updatedAt: '2026-05-01 10:30' },
    { key: '3', title: '2023年度工作总结', type: '报告', status: '已通过', creator: '系统管理员', updatedAt: '2026-04-30 17:00' },
  ];

  const showCreateModal = () => {
    Modal.confirm({
      title: '起草新公文',
      content: (
        <div style={{ marginTop: 16 }}>
          <p>请选择公文文种:</p>
          <Select placeholder="选择文种" style={{ width: '100%' }}>
            <Option value="1">通知</Option>
            <Option value="2">请示</Option>
            <Option value="3">报告</Option>
            <Option value="4">调研分析</Option>
            <Option value="5">经济信息</Option>
            <Option value="6">通用文档</Option>
          </Select>
          <p style={{ marginTop: 16 }}>公文标题:</p>
          <Input placeholder="输入公文标题" />
        </div>
      ),
      okText: '确认创建',
      cancelText: '取消',
      onOk: () => {
        const newId = Math.random().toString(36).substr(2, 9);
        navigate(`/workspace/${newId}`);
      },
    });
  };

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="公文管理中心"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={showCreateModal}>
            起草新公文
          </Button>
        }
      >
        <div style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
          <Input placeholder="搜索公文标题..." prefix={<SearchOutlined />} style={{ width: 300 }} />
          <Select placeholder="文种筛选" style={{ width: 150 }} allowClear>
            <Option value="notice">通知</Option>
            <Option value="report">报告</Option>
          </Select>
          <Select placeholder="状态筛选" style={{ width: 150 }} allowClear>
            <Option value="draft">起草中</Option>
            <Option value="submitted">审批中</Option>
            <Option value="approved">已通过</Option>
          </Select>
        </div>
        <Table columns={columns} dataSource={data} />
      </Card>
    </div>
  );
};

export default DocumentList;
