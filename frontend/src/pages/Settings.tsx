import React from 'react';
import { Layout, Typography, Card } from 'antd';
export const Settings: React.FC = () => (
  <Layout style={{ padding: 24, background: '#f0f2f5', minHeight: '100%' }}>
    <Typography.Title level={3}>系统中枢设置台 (System Settings)</Typography.Title>
    <Card>此处将展示用户矩阵管理、安全审计溯源及 Redis 锁监控大盘。</Card>
  </Layout>
);
