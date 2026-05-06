import React, { useState, useEffect } from 'react';
import { Table, Tag, Button, Space, Modal, message, Card, Typography, Input, Select, Badge } from 'antd';
import { 
  FileTextOutlined, 
  UploadOutlined, 
  DeleteOutlined, 
  HistoryOutlined, 
  SearchOutlined,
  EditOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../api/client';
import { useAuthStore } from '../../stores/authStore';

const { Title } = Typography;

export const Documents: React.FC = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const navigate = useNavigate();
  const userInfo = useAuthStore(state => state.userInfo);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/documents', { 
        params: { 
          page, 
          page_size: 10,
          status: statusFilter
        } 
      });
      setData(res.data.data.items);
      setTotal(res.data.data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [page, statusFilter]);

  const handleRevise = async (docId: string) => {
    try {
      await apiClient.post(`/documents/${docId}/revise`);
      message.success('已获取编辑锁，可重新修改公文');
      navigate(`/workspace/${docId}`);
    } catch (e: any) {
      message.error(e?.response?.data?.message || '回退失败，请重试');
    }
  };

  const handleDelete = (docId: string) => {
    Modal.confirm({
      title: '确认删除此公文？',
      content: '删除后将移入回收站（软删除），同时释放关联的编辑锁。',
      okText: '确认删除',
      okType: 'danger',
      onOk: async () => {
        await apiClient.delete(`/documents/${docId}`);
        message.success('公文已删除');
        fetchDocs();
      }
    });
  };

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: any) => (
        <Space>
          <FileTextOutlined style={{ color: '#1890ff' }} />
          <span style={{ fontWeight: 500 }}>{text || '未命名公文'}</span>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: any = {
          'DRAFTING': { color: 'blue', text: '起草中' },
          'SUBMITTED': { color: 'orange', text: '待科长审核' },
          'REVIEWED': { color: 'cyan', text: '科长已审' },
          'APPROVED': { color: 'green', text: '已签发' },
          'REJECTED': { color: 'red', text: '已驳回' },
          'ARCHIVED': { color: 'default', text: '已归档' },
        };
        const item = config[status] || { color: 'default', text: status };
        return <Tag color={item.color}>{item.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button 
            type="link" 
            icon={<EditOutlined />} 
            onClick={() => navigate(`/workspace/${record.doc_id}`)}
          >
            {record.status === 'DRAFTING' ? '编辑' : '查看'}
          </Button>
          {record.status === 'REJECTED' && (
             <Button type="link" onClick={() => handleRevise(record.doc_id)}>前往修改</Button>
          )}
          <Button type="text" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.doc_id)} />
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3} style={{ margin: 0 }}>公文管理中心</Title>
        <Space>
          <Select 
            placeholder="按状态筛选" 
            style={{ width: 120 }} 
            allowClear
            onChange={setStatusFilter}
          >
            <Select.Option value="DRAFTING">起草中</Select.Option>
            <Select.Option value="SUBMITTED">待科长审核</Select.Option>
            <Select.Option value="REVIEWED">科长已审</Select.Option>
            <Select.Option value="APPROVED">已签发</Select.Option>
            <Select.Option value="REJECTED">已驳回</Select.Option>
            <Select.Option value="ARCHIVED">已归档</Select.Option>
          </Select>
          <Input placeholder="搜索公文..." prefix={<SearchOutlined />} style={{ width: 250 }} />
        </Space>
      </div>

      <Card>
        <Table 
          columns={columns} 
          dataSource={data} 
          loading={loading}
          rowKey="doc_id"
          pagination={{ 
            total, 
            current: page, 
            pageSize: 10,
            onChange: (p) => setPage(p)
          }}
        />
      </Card>
    </div>
  );
};