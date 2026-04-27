import React, { useEffect, useState } from 'react';
import { Layout, Typography, Table, Button, Space, message, Modal, Input, Tag } from 'antd';
import apiClient from '../api/client';
import dayjs from 'dayjs';

const { Title } = Typography;
const { TextArea } = Input;

export const Approvals: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [reviewModalVisible, setReviewModalVisible] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/documents/', { params: { status: 'SUBMITTED' } });
      setData(res.data);
    } catch (e) {
      message.error('加载审批队列失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  const handleReview = async (isApproved: boolean) => {
    if (!isApproved && !rejectionReason) {
        return message.warning('请填写驳回理由');
    }
    try {
        await apiClient.post(`/approval/${selectedDoc.doc_id}/review`, {
            is_approved: isApproved,
            rejection_reason: isApproved ? null : rejectionReason
        });
        message.success(isApproved ? '公文已签署发布' : '公文已打回');
        setReviewModalVisible(false);
        setRejectionReason('');
        fetchQueue();
    } catch (e) {
        message.error('操作失败');
    }
  };

  const columns = [
    {
      title: '公文标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
        title: '起草人',
        dataIndex: 'creator_id',
        key: 'creator_id',
        render: (id: number) => `UID: ${id}` // 简化处理，实际应关联用户名
    },
    {
      title: '提交时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (val: string) => dayjs(val).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          <Button type="primary" size="small" onClick={() => {
              setSelectedDoc(record);
              setReviewModalVisible(true);
          }}>
            审核签署
          </Button>
          <Button size="small" href={`/workspace/${record.doc_id}`} target="_blank">
            预览原文
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Layout style={{ padding: 24, background: '#f0f2f5', minHeight: '100%' }} aria-label="签批管控容器">
      <Title level={3} style={{ color: '#003366' }}>科长签批管控台 (Approval Board)</Title>
      
      <Table 
        columns={columns} 
        dataSource={data} 
        rowKey="doc_id"
        loading={loading}
        style={{ background: '#fff' }}
        locale={{ emptyText: '暂无待审批公文' }}
      />

      <Modal
        title={`公文审核：${selectedDoc?.title}`}
        visible={reviewModalVisible}
        onCancel={() => setReviewModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setReviewModalVisible(false)}>取消</Button>,
          <Button key="reject" danger onClick={() => handleReview(false)}>驳回打回</Button>,
          <Button key="approve" type="primary" onClick={() => handleReview(true)}>批准签署 (SIP存证)</Button>
        ]}
      >
        <div style={{ marginBottom: 16 }}>
            <Tag color="orange">请确认：批准后将自动生成 SHA-256 司法防伪存证指纹并固化内容。</Tag>
        </div>
        <TextArea 
            placeholder="若选择驳回，请务必在此输入修改建议或驳回缘由..." 
            rows={4}
            value={rejectionReason}
            onChange={e => setRejectionReason(e.target.value)}
        />
      </Modal>
    </Layout>
  );
};
