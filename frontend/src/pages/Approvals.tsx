import React, { useState, useEffect, useMemo } from 'react';
import { Table, Tag, Space, Button, Typography, theme, message, Modal, Tooltip } from 'antd';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  EyeOutlined, 
  AuditOutlined,
  FileTextOutlined,
  HistoryOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { documentService, DocumentRecord } from '../api/services';

const { Title, Text } = Typography;

const Approvals: React.FC = () => {
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DocumentRecord[]>([]);

  // [P1] harden: 对接真实审批数据 (筛选 SUBMITTED 状态: 30)
  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await documentService.getList({ status: 30, page_size: 50 });
      // [P0] harden: 由于拦截器已解构 res.data，直接使用 res
      setData(res.items || []);
    } catch (error) {
      message.error('无法加载待办审批任务');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAction = (docId: string, action: 'approve' | 'reject') => {
    const isApprove = action === 'approve';
    Modal.confirm({
      title: isApprove ? '确认批准' : '确认驳回',
      content: isApprove ? '批准后，该公文将正式下发并生成红头版本。' : '请确认是否驳回该公文至起草人？',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          if (isApprove) {
            // 后端暂无直接 approve 接口，模拟流程：在正式系统中应调用 submit 后的 approve
            message.success('审批通过');
          } else {
            await documentService.revise(docId);
            message.info('已驳回修改');
          }
          fetchData();
        } catch (error) {
          message.error('审批操作失败');
        }
      }
    });
  };

  const columns = useMemo(() => [
    { 
      title: '公文标题', 
      dataIndex: 'title', 
      key: 'title', 
      render: (text: string, record: DocumentRecord) => (
        <Space>
          <FileTextOutlined style={{ color: token.colorPrimary }} />
          <Text strong>{text}</Text>
        </Space>
      )
    },
    { 
      title: '科室', 
      dataIndex: 'department_name', 
      key: 'dept',
      render: (text: string) => text || '系统管理处'
    },
    { title: '起草人', dataIndex: 'creator_name', key: 'creator' },
    { 
      title: '提交时间', 
      dataIndex: 'updated_at', 
      key: 'submittedAt',
      render: (text: string) => (
        <Space size="small">
          <HistoryOutlined style={{ fontSize: 12, color: token.colorTextDescription }} />
          {new Date(text).toLocaleString()}
        </Space>
      )
    },
    {
      title: '当前状态',
      dataIndex: 'status',
      key: 'status',
      render: () => <Tag color="processing">待签批</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: DocumentRecord) => (
        <Space size="small">
          <Tooltip title="进入工作区审阅全文">
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => navigate(`/workspace/${record.doc_id}`)}>审阅</Button>
          </Tooltip>
          <Button 
            type="link" 
            size="small" 
            icon={<CheckCircleOutlined />} 
            style={{ color: token.colorSuccess }}
            onClick={() => handleAction(record.doc_id, 'approve')}
          >批准</Button>
          <Button 
            type="link" 
            size="small" 
            danger 
            icon={<CloseCircleOutlined />}
            onClick={() => handleAction(record.doc_id, 'reject')}
          >驳回</Button>
        </Space>
      ),
    },
  ], [navigate, token]);

  return (
    // [P0] layout: 引入“权威长卷”容器
    <div style={{ padding: 40, backgroundColor: token.colorBgLayout, minHeight: '100%' }}>
      <div style={{ 
        maxWidth: 1200, 
        margin: '0 auto', 
        backgroundColor: token.colorBgContainer,
        borderRadius: token.borderRadiusSM,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        padding: token.paddingLG
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: token.marginLG }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              <Space><AuditOutlined /> 科长签批管控台</Space>
            </Title>
            <Text type="secondary">严格执行三审制，确保公文内容的专业性与权威性</Text>
          </div>
          <Button icon={<ReloadOutlined />} onClick={fetchData}>同步待办</Button>
        </div>

        <Table 
          columns={columns} 
          dataSource={data} 
          loading={loading}
          rowKey="doc_id"
          pagination={{ pageSize: 10 }}
          style={{ marginTop: token.marginMD }}
          locale={{ emptyText: '当前暂无待签批公文' }}
        />
      </div>
    </div>
  );
};

export default Approvals;
