import React, { useState, useEffect, useRef } from 'react';
import { Layout, Input, Button, Card, List, Typography, Space, Tooltip, Empty, message, Badge } from 'antd';
import { SendOutlined, DatabaseOutlined, RobotOutlined, UserOutlined, ApartmentOutlined } from '@ant-design/icons';
import { VirtualDocTree } from '../components/Workspace/VirtualDocTree';
import { useEditorStore } from '../store/useEditorStore';
import apiClient from '../api/client';
import { useAuthStore } from '../store/useAuthStore';

const { Sider, Content } = Layout;
const { Text, Paragraph } = Typography;

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  id: string;
}

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const context_kb_ids = useEditorStore(state => state.context_kb_ids);
  const userInfo = useAuthStore(state => state.userInfo);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;
    if (context_kb_ids.length === 0) {
      message.warning('请先从左侧勾选统计台账作为问答上下文');
      return;
    }

    const userMsg: ChatMessage = {
      role: 'user',
      content: inputValue,
      id: Date.now().toString()
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setLoading(true);

    try {
      const res = await apiClient.post('/chat/', {
        query: inputValue,
        context_kb_ids: context_kb_ids
      });

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.data,
        id: (Date.now() + 1).toString()
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      message.error(err.response?.data?.detail || '问答引擎暂时失联');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout style={{ height: 'calc(100vh - 88px)', background: '#f0f2f5' }}>
      <Sider width={300} style={{ background: '#fff', borderRight: '1px solid #d9d9d9', overflow: 'auto', padding: '16px' }}>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <DatabaseOutlined style={{ color: '#003366' }} />
            <Text strong>统计资料挂载区</Text>
            <Badge count={context_kb_ids.length} style={{ backgroundColor: '#003366' }} />
          </Space>
          <div style={{ fontSize: '12px', color: '#888', marginTop: 8 }}>
            勾选下方文件，AI 将穿透检索这些资料回答您的问题
          </div>
        </div>
        <VirtualDocTree />
      </Sider>

      <Content style={{ display: 'flex', flexDirection: 'column', padding: '24px' }}>
        <div 
          ref={scrollRef}
          style={{ flex: 1, overflowY: 'auto', marginBottom: 24, padding: '0 16px' }}
        >
          {messages.length === 0 ? (
            <Empty 
              image={<RobotOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />}
              description={
                <span>
                  我是泰兴统计 HRAG 助手<br />
                  请在左侧勾选台账后开始问答
                </span>
              }
              style={{ marginTop: 100 }}
            />
          ) : (
            <List
              dataSource={messages}
              renderItem={(item) => (
                <div style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: item.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 24 
                }}>
                  <Space style={{ marginBottom: 8 }}>
                    {item.role === 'assistant' ? <RobotOutlined style={{ color: '#003366' }} /> : null}
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {item.role === 'assistant' ? '政务 AI 助手' : userInfo?.username}
                    </Text>
                    {item.role === 'user' ? <UserOutlined /> : null}
                  </Space>
                  <Card 
                    size="small"
                    style={{ 
                      maxWidth: '80%', 
                      borderRadius: 12,
                      backgroundColor: item.role === 'user' ? '#003366' : '#fff',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
                    }}
                    bodyStyle={{ padding: '12px 16px' }}
                  >
                    <Text style={{ color: item.role === 'user' ? '#fff' : '#333' }}>
                      {item.content}
                    </Text>
                  </Card>
                </div>
              )}
            />
          )}
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
              <RobotOutlined spin style={{ color: '#003366' }} />
              <Text type="secondary">正在研读资料并组织答案...</Text>
            </div>
          )}
        </div>

        <div style={{ background: '#fff', padding: '16px', borderRadius: 8, boxShadow: '0 -2px 10px rgba(0,0,0,0.05)' }}>
          <Space.Compact style={{ width: '100%' }}>
            <Input 
              placeholder="请输入您的统计咨询问题..." 
              size="large"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onPressEnter={handleSend}
              disabled={loading}
            />
            <Button 
              type="primary" 
              icon={<SendOutlined />} 
              size="large"
              onClick={handleSend}
              loading={loading}
              style={{ background: '#003366' }}
            >
              询问
            </Button>
          </Space.Compact>
          <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              <ApartmentOutlined /> 当前挂载范围: {context_kb_ids.length > 0 ? `已挂载 ${context_kb_ids.length} 个节点` : '未挂载资料'}
            </Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              基于 bge-m3 语义引擎
            </Text>
          </div>
        </div>
      </Content>
    </Layout>
  );
};
