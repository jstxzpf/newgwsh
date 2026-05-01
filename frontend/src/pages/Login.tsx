import React, { useState } from 'react';
import { Card, Form, Input, Button, message, Layout } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

const { Content } = Layout;

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      // Mock login for now
      if (values.username === 'admin' && values.password === '123456') {
        const mockUser = {
          user_id: 1,
          username: 'admin',
          full_name: '系统管理员',
          role_level: 99,
          dept_id: 1,
          department_name: '办公室',
        };
        setAuth('mock-token', mockUser);
        message.success('登录成功');
        navigate('/dashboard');
      } else {
        message.error('用户名或密码错误');
      }
    } catch (error) {
      message.error('登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Card style={{ width: 400, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <h2 style={{ color: '#003366', margin: 0 }}>泰兴调查队公文处理系统</h2>
            <p style={{ color: '#666', marginTop: 8 }}>V3.0 智慧公文中心</p>
          </div>
          <Form
            name="login_form"
            initialValues={{ remember: true }}
            onFinish={onFinish}
            size="large"
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input prefix={<UserOutlined />} placeholder="工号 / 用户名" />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" block loading={loading}>
                登 录
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Content>
    </Layout>
  );
};

export default Login;
