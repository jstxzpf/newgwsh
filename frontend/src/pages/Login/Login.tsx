import React, { useState } from 'react';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../api/client';
import { useAuthStore } from '../../stores/authStore';
import './Login.css';

const { Title, Text } = Typography;

export const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setToken = useAuthStore(state => state.setToken);
  const setUserInfo = useAuthStore(state => state.setUserInfo);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      // 1. 登录获取 Token
      const loginRes = await apiClient.post('/auth/login', values);
      const { access_token } = loginRes.data.data;
      setToken(access_token);

      // 2. 立即补全用户信息（IRON RULE: 用于水印等单一数据源）
      const meRes = await apiClient.get('/auth/me');
      setUserInfo(meRes.data.data);

      message.success('欢迎回来');
      navigate('/dashboard');
    } catch (err: any) {
      // apiClient 已统一处理错误弹窗，此处仅重置 loading
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-bg-overlay" />
      <Card className="login-card" bordered={false}>
        <div className="login-header">
          <img src="/logo.png" alt="Logo" className="login-logo" />
          <Title level={3} style={{ color: '#003366', margin: 0 }}>
            国家统计局泰兴调查队
          </Title>
          <Text type="secondary">公文处理系统 V3.0</Text>
        </div>

        <Form
          name="login"
          size="large"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入工号' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="工号" />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              进入系统
            </Button>
          </Form.Item>
        </Form>
        
        <div className="login-footer">
          <Text type="disabled">© 2026 国家统计局泰兴调查队 版权所有</Text>
        </div>
      </Card>
    </div>
  );
};