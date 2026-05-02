import React, { useState, useMemo, useEffect } from 'react';
import { Table, Tag, Space, Button, Input, Modal, Select, Form, Typography, theme, message } from 'antd';
import { SearchOutlined, PlusOutlined, EditOutlined, DownloadOutlined, DeleteOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { documentService, DocumentRecord } from '../api/services';

const { Option } = Select;
const { Title, Text } = Typography;

const DocumentList: React.FC = () => {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DocumentRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [params, setParams] = useState({ page: 1, page_size: 10, title: '', type: undefined, status: undefined });

  // [P1] harden: 真实数据对接 - 加载列表
  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await documentService.getList(params);
      // [P0] harden: 由于拦截器已解构 res.data，直接使用 res
      setData(res.items || []);
      setTotal(res.total || 0);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [params]);

  // [P2] optimize: 使用 useMemo 包裹 columns，定义严格类型
  const columns = useMemo(() => [
    { 
      title: '标题', 
      dataIndex: 'title', 
      key: 'title', 
      render: (text: string, record: DocumentRecord) => (
        <Space>
          <FileTextOutlined style={{ color: token.colorPrimary }} />
          <a onClick={() => navigate(`/workspace/${record.doc_id}`)} style={{ fontWeight: 500, color: token.colorText }}>
            {text}
          </a>
        </Space>
      ) 
    },
    { 
      title: '文种', 
      dataIndex: 'doc_type', 
      key: 'type', 
      render: (text: string) => (
        <Tag color="default" style={{ border: `1px solid ${token.colorPrimary}`, color: token.colorPrimary, backgroundColor: `${token.colorPrimary}08` }}>
          {text}
        </Tag>
      ) 
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'default';
        if (status === '已通过' || status === 'APPROVED') color = 'success';
        if (status === '审批中' || status === 'SUBMITTED') color = 'processing';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    { title: '起草人', dataIndex: 'creator_name', key: 'creator' },
    { title: '最后更新', dataIndex: 'updated_at', key: 'updatedAt' },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: DocumentRecord) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => navigate(`/workspace/${record.doc_id}`)}>编辑</Button>
          {(record.status === '已通过' || record.status === 'APPROVED') && (
            <Button 
              type="link" 
              size="small" 
              icon={<DownloadOutlined />}
              onClick={() => window.open(documentService.download(record.doc_id))}
            >下载</Button>
          )}
          <Button 
            type="link" 
            size="small" 
            danger 
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.doc_id)}
          >删除</Button>
        </Space>
      ),
    },
  ], [navigate, token]);

  const handleDelete = (docId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '公文删除后将无法恢复，是否确认？',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await documentService.delete(docId);
          message.success('删除成功');
          fetchData();
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      // [P1] harden: 真实异步创建逻辑
      const res = await documentService.init({
        doc_type_id: parseInt(values.type),
        title: values.title
      });
      message.success('创建成功');
      setIsModalOpen(false);
      // [P0] harden: 由于拦截器已解构 res.data，直接使用 res.doc_id
      navigate(`/workspace/${res.doc_id}`);
    } catch (error: any) {
      if (error.errorFields) return; // 表单校验不通过
      message.error(error.response?.data?.message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: token.paddingLG, backgroundColor: token.colorBgLayout, minHeight: '100%' }}>
      <div style={{ 
        maxWidth: 1200, 
        margin: '0 auto', 
        backgroundColor: token.colorBgContainer,
        borderRadius: token.borderRadiusSM,
        boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
        padding: token.paddingLG
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: token.marginLG }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>公文管理中心</Title>
            <Text type="secondary">高效、规范地完成公文的全生命周期管理</Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalOpen(true)}>
            起草新公文
          </Button>
        </div>

        <div style={{ marginBottom: token.marginMD, display: 'flex', gap: token.marginMD }}>
          <Input 
            placeholder="搜索公文标题..." 
            prefix={<SearchOutlined />} 
            style={{ width: 320 }} 
            onPressEnter={(e) => setParams({ ...params, page: 1, title: e.currentTarget.value })}
            allowClear
            onChange={(e) => !e.target.value && setParams({ ...params, page: 1, title: '' })}
          />
          <Select 
            placeholder="文种筛选" 
            style={{ width: 160 }} 
            allowClear 
            onChange={(val) => setParams({ ...params, page: 1, type: val })}
          >
            <Option value="1">通知</Option>
            <Option value="2">请示</Option>
            <Option value="3">报告</Option>
          </Select>
          <Select 
            placeholder="状态筛选" 
            style={{ width: 160 }} 
            allowClear
            onChange={(val) => setParams({ ...params, page: 1, status: val })}
          >
            <Option value={10}>起草中</Option>
            <Option value={30}>审批中</Option>
            <Option value={40}>已通过</Option>
          </Select>
        </div>

        <Table 
          columns={columns} 
          dataSource={data} 
          loading={loading}
          rowKey="doc_id"
          pagination={{ 
            total, 
            current: params.page, 
            pageSize: params.page_size,
            onChange: (page) => setParams({ ...params, page })
          }}
          style={{ marginTop: token.marginMD }}
        />
      </div>

      <Modal
        title="起草新公文"
        open={isModalOpen}
        onOk={handleCreate}
        confirmLoading={loading}
        onCancel={() => setIsModalOpen(false)}
        okText="确认创建"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: token.marginLG }}>
          <Form.Item
            name="type"
            label="公文文种"
            rules={[{ required: true, message: '请选择公文文种' }]}
          >
            <Select placeholder="选择文种">
              <Option value="1">通知</Option>
              <Option value="2">请示</Option>
              <Option value="3">报告</Option>
              <Option value="4">调研分析</Option>
              <Option value="5">经济信息</Option>
              <Option value="6">通用文档</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="title"
            label="公文标题"
            rules={[{ required: true, message: '请输入公文标题' }]}
          >
            <Input placeholder="输入公文标题" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DocumentList;
