import React, { useState, useEffect } from 'react';
import { Layout, List, Card, Typography, Button, Space, Badge, Modal, Input, message, Empty, Divider, Popconfirm, Tabs } from 'antd';
import {
  InboxOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined,
  SendOutlined
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { useAuthStore } from '../../stores/authStore';
import { EditorA4Paper } from '../../components/common/EditorA4Paper/EditorA4Paper';
import './Approvals.css';

const { Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;

export const Approvals: React.FC = () => {
  const userInfo = useAuthStore(state => state.userInfo);
  const isAdmin = (userInfo?.role_level ?? 0) >= 99;
  const canReview = (userInfo?.role_level ?? 0) >= 5;

  const [docs, setDocs] = useState<any[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [contentLoading, setContentLoading] = useState(false);
  const [rejectionVisible, setRejectionVisible] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [activeTab, setActiveTab] = useState<string>('SUBMITTED');

  const fetchDocs = async (status: string) => {
    setLoading(true);
    try {
      const res = await apiClient.get('/documents', { params: { status } });
      setDocs(res.data.data.items);
      setSelectedDoc(null);
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
    fetchDocs(activeTab);
  }, [activeTab]);

  // 科长审核：SUBMITTED → REVIEWED
  const handleReview = () => {
    Modal.confirm({
      title: '确认审核通过？',
      content: '审核通过后公文将提交局长签发。',
      okText: '审核通过',
      onOk: async () => {
        await apiClient.post(`/approval/${selectedDoc.doc_id}/review`, { action: 'APPROVE' });
        message.success('审核通过，已提交局长签发');
        setSelectedDoc(null);
        fetchDocs(activeTab);
      }
    });
  };

  // 局长签发：REVIEWED → APPROVED
  const handleIssue = () => {
    Modal.confirm({
      title: '确认签发？',
      content: '签发后将生成发文编号和不可篡改的 SIP 数字指纹，并自动启动国标排版任务。此操作不可撤销。',
      okText: '确认签发',
      onOk: async () => {
        const res = await apiClient.post(`/approval/${selectedDoc.doc_id}/issue`);
        message.success(`签发成功，发文编号：${res.data.data.document_number}`);
        setSelectedDoc(null);
        fetchDocs(activeTab);
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
    fetchDocs(activeTab);
  };

  const tabItems = [
    ...(canReview ? [{ key: 'SUBMITTED', label: '科长审核' }] : []),
    ...(isAdmin ? [{ key: 'REVIEWED', label: '局长签发' }] : []),
  ];

  if (tabItems.length === 0) {
    return <Empty description="您没有审批权限" />;
  }

  return (
    <Layout className="approval-layout">
      <Sider width={320} theme="light" className="approval-sider">
        <div className="sider-header">
           <Title level={4}><InboxOutlined /> 待办签批</Title>
           <Tabs
             activeKey={activeTab}
             onChange={setActiveTab}
             items={tabItems}
             size="small"
           />
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
                    <Text type="secondary">提交人: {item.creator_name || '科员'}</Text>
                    <Text type="secondary">{new Date(item.created_at).toLocaleString()}</Text>
                  </Space>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: <Empty description={activeTab === 'SUBMITTED' ? '暂无待审核公文' : '暂无待签发公文'} /> }}
        />
      </Sider>

      <Content className="approval-content">
        {selectedDoc ? (
          <div className="audit-view">
             <div className="audit-toolbar">
                <Space>
                   <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
                   <Title level={5} style={{ margin: 0 }}>深核查视窗: {selectedDoc.title}</Title>
                   {selectedDoc.status === 'REVIEWED' && (
                     <Badge status="processing" text="科长已审核" />
                   )}
                </Space>
                <Space>
                   <Button danger icon={<CloseCircleOutlined />} onClick={() => setRejectionVisible(true)}>驳回打回</Button>
                   {activeTab === 'SUBMITTED' ? (
                     <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleReview} style={{ background: '#003366' }}>审核通过</Button>
                   ) : (
                     <Button type="primary" icon={<SendOutlined />} onClick={handleIssue} style={{ background: '#003366' }}>局长签发</Button>
                   )}
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