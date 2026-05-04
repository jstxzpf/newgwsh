import React, { useState, useEffect } from 'react';
import { Layout, List, Card, Typography, Button, Space, Badge, Modal, Input, message, Empty, Divider, Popconfirm } from 'antd';
import { 
  InboxOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { EditorA4Paper } from '../../components/common/EditorA4Paper/EditorA4Paper';
import './Approvals.css';

const { Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;

export const Approvals: React.FC = () => {
  const [docs, setDocs] = useState<any[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [contentLoading, setContentLoading] = useState(false);
  const [rejectionVisible, setRejectionVisible] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  const fetchSubmittedDocs = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/documents', { params: { status: 'SUBMITTED' } });
      setDocs(res.data.data.items);
      if (res.data.data.items.length > 0 && !selectedDoc) {
        handleSelectDoc(res.data.data.items[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDoc = async (doc: any) => {
    setContentLoading(true);
    try {
      const res = await apiClient.get(`/documents/${doc.doc_id}`);
      setSelectedDoc(res.data.data);
    } finally {
      setContentLoading(false);
    }
  };

  useEffect(() => {
    fetchSubmittedDocs();
  }, []);

  const handleApprove = () => {
    Modal.confirm({
      title: '确认批准并签署？',
      content: '签署后将生成不可篡改的 SIP 数字指纹，并自动启动国标排版任务。此操作不可撤销。',
      okText: '签署批准',
      onOk: async () => {
        await apiClient.post(`/approval/${selectedDoc.doc_id}/review`, { action: 'APPROVE' });
        message.success('审批通过，存证指纹已生成');
        setSelectedDoc(null);
        fetchSubmittedDocs();
      }
    });
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) {
      return message.error('请填写驳回理由');
    }
    await apiClient.post(`/approval/${selectedDoc.doc_id}/review`, { 
      action: 'REJECT', 
      comments: rejectionReason 
    });
    message.warning('公文已驳回');
    setRejectionVisible(false);
    setRejectionReason('');
    setSelectedDoc(null);
    fetchSubmittedDocs();
  };

  return (
    <Layout className="approval-layout">
      <Sider width={320} theme="light" className="approval-sider">
        <div className="sider-header">
           <Title level={4}><InboxOutlined /> 待办签批</Title>
           <Divider style={{ margin: '12px 0' }} />
        </div>
        <List
          loading={loading}
          dataSource={docs}
          className="approval-list"
          renderItem={(item) => (
            <List.Item 
              className={`approval-item ${selectedDoc?.doc_id === item.doc_id ? 'active' : ''}`}
              onClick={() => handleSelectDoc(item)}
            >
              <List.Item.Meta
                title={item.title || '未命名公文'}
                description={
                  <Space direction="vertical" size={0}>
                    <Text type="secondary" size="small">提交人: {item.creator_name || '科员'}</Text>
                    <Text type="secondary" size="small">{new Date(item.created_at).toLocaleString()}</Text>
                  </Space>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: <Empty description="暂无待审批公文" /> }}
        />
      </Sider>

      <Content className="approval-content">
        {selectedDoc ? (
          <div className="audit-view">
             <div className="audit-toolbar">
                <Space>
                   <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
                   <Title level={5} style={{ margin: 0 }}>深核查视窗: {selectedDoc.title}</Title>
                </Space>
                <Space>
                   <Button danger icon={<CloseCircleOutlined />} onClick={() => setRejectionVisible(true)}>驳回打回</Button>
                   <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleApprove} style={{ background: '#003366' }}>批准并签署</Button>
                </Space>
             </div>
             
             <div className="a4-preview-container">
                <EditorA4Paper>
                   <Paragraph className="preview-text">
                      {selectedDoc.content || '（正文为空）'}
                   </Paragraph>
                </EditorA4Paper>
             </div>
          </div>
        ) : (
          <div className="empty-audit">
             <Empty description="请在左侧选择需要审阅的公文" />
          </div>
        )}
      </Content>

      <Modal
        title="填写驳回理由"
        open={rejectionVisible}
        onOk={handleReject}
        onCancel={() => setRejectionVisible(false)}
        okText="确认驳回"
        okType="danger"
      >
        <Input.TextArea 
          rows={4} 
          placeholder="请输入详细的驳回理由，将推送给起草人..." 
          value={rejectionReason}
          onChange={(e) => setRejectionReason(e.target.value)}
        />
      </Modal>
    </Layout>
  );
};