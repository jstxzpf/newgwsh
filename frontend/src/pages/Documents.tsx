import React, { useEffect, useState } from 'react';
import { Layout, Typography, Table, Tag, Button, Space, Input, Select, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import { FileTextOutlined, SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { Content } = Layout;
const { Title } = Typography;
const { Option } = Select;

export const Documents: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/documents/', {
        params: { 
            status: filterStatus,
            page_size: 100 // 简化处理，拉取近期 100 条
        }
      });
      setData(res.data);
    } catch (e) {
      message.error('无法拉取公文列表');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [filterStatus]);

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: any) => (
        <Space>
          <FileTextOutlined style={{ color: '#003366' }} />
          <a onClick={() => navigate(`/workspace/${record.doc_id}`)}>{text}</a>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: any = {
          'DRAFTING': 'blue',
          'SUBMITTED': 'orange',
          'APPROVED': 'green',
          'REJECTED': 'red'
        };
        const textMap: any = {
          'DRAFTING': '起草中',
          'SUBMITTED': '审批中',
          'APPROVED': '已结项',
          'REJECTED': '被驳回'
        };
        return <Tag color={colorMap[status]}>{textMap[status]}</Tag>;
      },
    },
    {
      title: '最后修改',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button size="small" onClick={() => navigate(`/workspace/${record.doc_id}`)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <Layout style={{ padding: 24, background: '#f0f2f5', minHeight: '100%' }} aria-label="公文管理容器">
      <Title level={3} style={{ color: '#003366' }}>公文管理中心 (Document Center)</Title>
      
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', gap: 16 }}>
        <Space>
          <Input 
            placeholder="搜索标题..." 
            prefix={<SearchOutlined />} 
            style={{ width: 250 }}
            onChange={e => setSearchText(e.target.value)}
          />
          <Select 
            placeholder="按状态筛选" 
            style={{ width: 150 }} 
            allowClear
            onChange={val => setFilterStatus(val)}
          >
            <Option value="DRAFTING">起草中</Option>
            <Option value="SUBMITTED">审批中</Option>
            <Option value="APPROVED">已结项</Option>
            <Option value="REJECTED">被驳回</Option>
          </Select>
        </Space>
        <Button type="primary" onClick={() => fetchDocuments()}>刷新列表</Button>
      </div>

      <Table 
        columns={columns} 
        dataSource={data.filter((item: any) => item.title.includes(searchText))} 
        rowKey="doc_id"
        loading={loading}
        pagination={{ pageSize: 10 }}
        style={{ background: '#fff' }}
      />
    </Layout>
  );
};
