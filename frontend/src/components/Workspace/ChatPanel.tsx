import React, { useState } from 'react';
import { Drawer, Input, Button, Spin, List, Typography } from 'antd';
import { MessageOutlined, SendOutlined } from '@ant-design/icons';
import { useEditorStore } from '../../store/useEditorStore';
import apiClient from '../../api/client';

const { Text } = Typography;

export const ChatPanel: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<{role: 'user'|'ai', content: string}[]>([]);
  const { context_kb_ids } = useEditorStore();

  const handleSend = async () => {
    if (!query.trim()) return;
    
    const userMsg = query;
    setQuery('');
    setHistory(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await apiClient.post('/chat/', {
        query: userMsg,
        context_kb_ids: context_kb_ids
      });
      setHistory(prev => [...prev, { role: 'ai', content: res.data.answer }]);
    } catch (e) {
      setHistory(prev => [...prev, { role: 'ai', content: '❌ 请求算力节点失败。' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button 
        type="primary" 
        shape="circle" 
        icon={<MessageOutlined />} 
        size="large"
        style={{ 
          position: 'fixed', 
          right: 40, 
          bottom: 40, 
          zIndex: 100, 
          backgroundColor: '#003366', 
          width: 56, 
          height: 56, 
          boxShadow: '0 4px 12px rgba(0,51,102,0.4)',
          border: 'none'
        }}
        onClick={() => setVisible(true)}
      />
      <Drawer
        title="🤖 穿透式智能问答 (HRAG)"
        placement="right"
        onClose={() => setVisible(false)}
        open={visible}
        width={400}
        styles={{ body: { display: 'flex', flexDirection: 'column', padding: 0 } }}
      >
        <div style={{ padding: '12px 16px', background: '#e6f4ff', borderBottom: '1px solid #91caff', fontSize: '12px', color: '#0958d9' }}>
          当前已挂载 <strong>{context_kb_ids.length}</strong> 个知识库特征域。
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
          <List
            dataSource={history}
            renderItem={item => (
              <List.Item style={{ borderBottom: 'none', padding: '4px 0' }}>
                <div style={{ 
                  background: item.role === 'user' ? '#f0f0f0' : '#e6f7ff', 
                  padding: '8px 12px', 
                  borderRadius: '8px', 
                  width: '100%',
                  border: item.role === 'user' ? '1px solid #d9d9d9' : '1px solid #91caff'
                }}>
                  <div style={{ fontSize: '11px', color: '#888', marginBottom: 4 }}>{item.role === 'user' ? '您' : '政务助手'}</div>
                  <Text style={{ whiteSpace: 'pre-wrap', fontSize: '14px' }}>{item.content}</Text>
                </div>
              </List.Item>
            )}
          />
          {loading && <div style={{ textAlign: 'center', margin: '20px 0' }}><Spin tip="AI 推理中..." /></div>}
        </div>
        <div style={{ padding: '16px', borderTop: '1px solid #f0f0f0', display: 'flex', gap: '8px' }}>
          <Input 
            value={query} 
            onChange={e => setQuery(e.target.value)} 
            onPressEnter={handleSend}
            placeholder="询问有关挂载台账的问题..." 
            disabled={loading}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} style={{ backgroundColor: '#003366', border: 'none' }} />
        </div>
      </Drawer>
    </>
  );
};
