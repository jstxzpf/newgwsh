import React, { useState } from 'react';
import { Card, Form, Input, Button, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';

const { Title } = Typography;

export const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setToken = useAuthStore(state => state.setToken);
  const setUserInfo = useAuthStore(state => state.setUserInfo);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', values.username);
      formData.append('password', values.password);

      const res = await apiClient.post('/auth/login', formData);
      setToken(res.data.access_token);
      
      // 获取用户信息
      const meRes = await apiClient.get('/auth/me');
      setUserInfo({
        userId: meRes.data.user_id,
        username: meRes.data.username,
        deptId: meRes.data.dept_id,
        deptName: meRes.data.dept_name,
        roleLevel: meRes.data.role_level
      });

      message.success('登录成功');
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      height: '100vh', 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      background: '#f0f2f5',
      backgroundImage: 'radial-gradient(#d9d9d9 1px, transparent 1px)',
      backgroundSize: '20px 20px'
    }}>
      <Card style={{ width: 400, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title level={3} style={{ color: '#003366', margin: 0 }}>统计公文智能写作系统</Title>
          <div style={{ color: '#888', marginTop: 8 }}>政务内网安全登录</div>
        </div>
        
        <Form
          name="login"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading} style={{ backgroundColor: '#003366', border: 'none' }}>
              登 录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};
