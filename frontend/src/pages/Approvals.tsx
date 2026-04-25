import React from 'react';
import { Layout, Typography, Card } from 'antd';
export const Approvals: React.FC = () => (
  <Layout style={{ padding: 24, background: '#f0f2f5', minHeight: '100%' }}>
    <Typography.Title level={3}>科长签批管控台 (Approval Board)</Typography.Title>
    <Card>此处将展示待审核公文列表及 SIP 存证预览。</Card>
  </Layout>
);
