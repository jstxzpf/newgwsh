import React, { useEffect, useState } from 'react';
import { Radio, List, Spin, Empty, Popconfirm, message, Button } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { apiClient } from '../../../api/client';
import { useEditorStore } from '../../../stores/editorStore';
import { useAuthStore } from '../../../stores/authStore';

export const ExemplarPanel: React.FC = () => {
  const [exemplars, setExemplars] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const docTypeId = useEditorStore(state => state.docTypeId);
  const exemplarId = useEditorStore(state => state.exemplarId);
  const setExemplarId = (id: number | null) => useEditorStore.setState({ exemplarId: id });
  const userInfo = useAuthStore(state => state.userInfo);
  const canDelete = (userInfo?.role_level ?? 0) >= 99 || (userInfo?.is_dept_head ?? false);

  const fetchExemplars = async () => {
    if (!docTypeId) return;
    try {
      const res = await apiClient.get('/exemplars', { params: { doc_type_id: docTypeId } });
      setExemplars(res.data.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExemplars();
  }, [docTypeId]);

  const handleDelete = async (id: number) => {
    try {
      await apiClient.delete(`/exemplars/${id}`);
      message.success('范文已删除');
      if (exemplarId === id) setExemplarId(null);
      fetchExemplars();
    } catch (e: any) {
      message.error(e?.response?.data?.message || '删除失败');
    }
  };

  if (loading) return <Spin size="small" style={{ margin: '20px' }} />;
  if (exemplars.length === 0) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无对应范文" />;

  return (
    <div style={{ padding: '0 8px' }}>
      <Radio.Group
        style={{ width: '100%' }}
        value={exemplarId}
        onChange={(e) => setExemplarId(e.target.value)}
      >
        <List
          size="small"
          dataSource={exemplars}
          renderItem={(item) => (
            <List.Item
              actions={canDelete ? [
                <Popconfirm
                  key="del"
                  title="确认删除此范文？"
                  onConfirm={() => handleDelete(item.exemplar_id)}
                >
                  <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              ] : undefined}
            >
              <Radio value={item.exemplar_id}>{item.title}</Radio>
            </List.Item>
          )}
        />
      </Radio.Group>
    </div>
  );
};
