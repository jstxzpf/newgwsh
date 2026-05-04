import React, { useState, useRef } from 'react';
import { Layout, Input, List, Avatar, Typography, Space, Button, Card, Empty, Tooltip, Tag, Divider } from 'antd';
import { SendOutlined, UserOutlined, RobotOutlined, DeploymentUnitOutlined, BookOutlined } from '@ant-design/icons';
import { VirtualDocTree } from '../Workspace/components/VirtualDocTree';
import { useAuthStore } from '../../stores/authStore';
import { useEditorStore } from '../../stores/editorStore';
import './Chat.css';

const { Sider, Content } = Layout;
const { Text, Paragraph } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  isStreaming?: boolean;
}

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const userInfo = useAuthStore(state => state.userInfo);
  const context_kb_ids = useEditorStore(state => state.context_kb_ids);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: inputValue };
    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setLoading(true);

    // 添加 AI 占位
    const assistantMsg: Message = { role: 'assistant', content: '', isStreaming: true };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      // 铁律：必须使用 POST 且携带上下文 ID
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          query: userMsg.content,
          context_kb_ids: context_kb_ids
        })
      });

      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6));
            if (data.text) {
              fullContent += data.text;
              updateLastMessage(fullContent);
            }
            if (data.done) {
              updateLastMessage(fullContent, data.citations);
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      updateLastMessage("对话系统异常，请稍后再试。");
    } finally {
      setLoading(false);
    }
  };

  const updateLastMessage = (content: string, citations?: string[]) => {
    setMessages(prev => {
      const newMsgs = [...prev];
      const last = newMsgs[newMsgs.length - 1];
      last.content = content;
      last.citations = citations;
      last.isStreaming = false;
      return newMsgs;
    });
    // 自动滚动
    setTimeout(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, 50);
  };

  return (
    <Layout className="chat-layout">
      <Content className="chat-main">
        <div className="chat-history" ref={scrollRef}>
          {messages.length === 0 ? (
            <div className="chat-welcome">
               <Empty 
                  image={<RobotOutlined style={{ fontSize: 64, color: '#003366' }} />} 
                  description={
                    <span>
                      <Title level={4}>我是泰兴调查队智能助理</Title>
                      <Text type="secondary">请在右侧挂载台账范围，我将严格依据数据为您解答</Text>
                    </span>
                  }
               />
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className={`chat-bubble-container ${msg.role}`}>
                <Avatar icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />} />
                <div className="chat-bubble">
                   <Paragraph>{msg.content}</Paragraph>
                   {msg.citations && msg.citations.length > 0 && (
                     <div className="chat-citations">
                       <Divider style={{ margin: '8px 0' }} />
                       <Space size={[0, 4]} wrap>
                         <Text type="secondary" style={{ fontSize: 12 }}><BookOutlined /> 引用数据源：</Text>
                         {msg.citations.map((c, i) => (
                           <Tooltip key={i} title={c}>
                             <Tag size="small">来源 {i + 1}</Tag>
                           </Tooltip>
                         ))}
                       </Space>
                     </div>
                   )}
                </div>
              </div>
            ))
          )}
        </div>
        
        <div className="chat-input-area">
          <Input.TextArea
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="请输入您的统计业务咨询..."
            autoSize={{ minRows: 2, maxRows: 6 }}
            onPressEnter={e => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <Button 
            type="primary" 
            icon={<SendOutlined />} 
            onClick={handleSend}
            className="btn-send"
            disabled={loading}
          />
        </div>
      </Content>

      <Sider width={280} theme="light" className="chat-sider">
         <div className="scoped-panel">
            <div className="scoped-header">
               <DeploymentUnitOutlined /> <Text strong>检索域限定 (Scope)</Text>
            </div>
            <Divider style={{ margin: '12px 0' }} />
            <div className="scoped-tree-container">
               <VirtualDocTree />
            </div>
            <div className="scoped-footer">
               <Text type="secondary" size="small">勾选文件夹或文件以作为 AI 研读的上下文边界。</Text>
            </div>
         </div>
      </Sider>
    </Layout>
  );
};