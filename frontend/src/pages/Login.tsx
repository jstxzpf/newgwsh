import React, { useState } from 'react';
import { Card, Form, Input, Button, message, Layout } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { authService } from '../api/services';

const { Content } = Layout;

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      // 1. 调用真实登录接口
      const loginRes = await authService.login({
        username: values.username,
        password: values.password
      });
      const access_token = loginRes.access_token;
      
      // 2. 更新全局状态 (先只设置 token，以便 me() 接口能带上 token)
      setAuth(access_token, null as any);
      
      // 3. 获取当前用户信息
      const user = await authService.me();
      
      // 4. 补全用户信息
      setAuth(access_token, user);
      
      message.success('登录成功');
      navigate('/dashboard');
    } catch (error: any) {
      console.error('Login failed:', error);
      message.error(error.message || '登录失败，请检查网络或凭据');
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
