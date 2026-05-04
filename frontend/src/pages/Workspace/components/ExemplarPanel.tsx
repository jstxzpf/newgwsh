import React, { useEffect, useState } from 'react';
import { Radio, List, Spin, Empty, Space } from 'antd';
import { apiClient } from '../../../api/client';
import { useEditorStore } from '../../../stores/editorStore';

export const ExemplarPanel: React.FC = () => {
  const [exemplars, setExemplars] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { docTypeId, exemplarId, setExemplarId } = useEditorStore(state => ({
    docTypeId: state.docTypeId,
    exemplarId: state.exemplarId,
    setExemplarId: (id: number | null) => (useEditorStore.setState({ exemplarId: id }))
  }));

  useEffect(() => {
    const fetchExemplars = async () => {
      if (!docTypeId) return;
      try {
        const res = await apiClient.get(`/exemplars`, { params: { doc_type_id: docTypeId } });
        setExemplars(res.data.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchExemplars();
  }, [docTypeId]);

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
            <List.Item>
              <Radio value={item.exemplar_id}>{item.title}</Radio>
            </List.Item>
          )}
        />
      </Radio.Group>
    </div>
  );
};