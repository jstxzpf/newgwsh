import React from 'react';
import { Layout, Typography, Card } from 'antd';
export const Documents: React.FC = () => (
  <Layout style={{ padding: 24, background: '#f0f2f5', minHeight: '100%' }}>
    <Typography.Title level={3}>公文管理中心 (Document Management)</Typography.Title>
    <Card>此处将展示公文管理列表，支持按科室与状态筛选。</Card>
  </Layout>
);
