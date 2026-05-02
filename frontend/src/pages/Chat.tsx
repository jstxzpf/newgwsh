import React, { useState } from 'react';
import { Card, Input, Button, List, Avatar, Divider, Layout, Tree, Typography, Space } from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined, MessageOutlined } from '@ant-design/icons';

import { useAuthStore } from '../stores/authStore';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

const Chat: React.FC = () => {
  const { token } = useAuthStore();
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '您好，我是泰兴调查队政务助手。您可以向我咨询挂载知识库中的统计指标或政策法规。' }
  ]);
  const [inputValue, setInputValue] = useState('');

  const handleSend = async () => {
    if (!inputValue.trim()) return;
    
    const query = inputValue;
    const newMsg = { role: 'user', content: query };
    setMessages(prev => [...prev, newMsg]);
    setInputValue('');

    const aiMsgId = Date.now();
    setMessages(prev => [...prev, { role: 'assistant', content: '', id: aiMsgId } as any]);

    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token || ''}`
        },
        body: JSON.stringify({ query, context_kb_ids: [] }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let aiContent = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.token) {
                  aiContent += data.token;
                  setMessages(prev => prev.map((m, idx) => 
                    (idx === prev.length - 1) ? { ...m, content: aiContent } : m
                  ));
                }
              } catch (e) {}
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
    }
  };

  return (
    <Layout style={{ height: 'calc(100vh - 64px - 24px)', background: '#fff' }}>
      <Sider width={280} theme="light" style={{ borderRight: '1px solid #e8e8e8', padding: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>
            <Space><MessageOutlined /> 智能咨询助手</Space>
          </Title>
        </div>
        <Divider style={{ margin: '12px 0' }} />
        <h3>知识挂载范围</h3>
        <p style={{ fontSize: 12, color: '#999' }}>勾选后 AI 将优先检索相关台账</p>
        <Divider style={{ margin: '12px 0' }} />
        <Tree
          checkable
          treeData={[
            { title: '全局库', key: 'base', children: [{ title: '统计法.pdf', key: 'kb-1' }] },
            { title: '科室共享', key: 'dept', children: [{ title: '2024一季度分析.docx', key: 'kb-2' }] },
          ]}
        />
      </Sider>
      
      <Content style={{ display: 'flex', flexDirection: 'column', padding: 24, background: '#f0f2f5' }}>
        <Card style={{ flex: 1, overflow: 'auto', marginBottom: 16 }} bodyStyle={{ padding: 16 }}>
          <List
            dataSource={messages}
            renderItem={(item) => (
              <List.Item style={{ borderBottom: 'none', justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div 
                  className={item.role === 'user' ? 'chat-message-user' : 'chat-message-ai'}
                  style={{ display: 'flex', flexDirection: item.role === 'user' ? 'row-reverse' : 'row', gap: 12, maxWidth: '80%' }}
                >
                  <Avatar icon={item.role === 'user' ? <UserOutlined /> : <RobotOutlined />} style={{ background: item.role === 'user' ? '#1890ff' : '#003366' }} />
                  <div style={{
                    background: item.role === 'user' ? '#1890ff' : '#fff',
                    color: item.role === 'user' ? '#fff' : '#000',
                    padding: '8px 16px',
                    borderRadius: 8,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                  }}>
                    {item.content}
                  </div>
                </div>
              </List.Item>
            )}
          />
        </Card>
        
        <div style={{ display: 'flex', gap: 12 }}>
          <Input
            size="large"
            placeholder="在此输入您的统计咨询问题..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={handleSend}
          />
          <Button type="primary" size="large" icon={<SendOutlined />} onClick={handleSend}>发送</Button>
        </div>
      </Content>
    </Layout>
  );
};

export default Chat;
