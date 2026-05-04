import React, { useEffect, useState } from 'react';
import { Tree, Spin, Empty } from 'antd';
import { apiClient } from '../../../api/client';
import { useEditorStore } from '../../../stores/editorStore';

export const VirtualDocTree: React.FC = () => {
  const [treeData, setTreeData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const context_kb_ids = useEditorStore(state => state.context_kb_ids);
  
  const setContextKbIds = (ids: number[]) => {
    useEditorStore.setState({ context_kb_ids: ids });
  };

  useEffect(() => {
    const fetchHierarchy = async () => {
      try {
        const res = await apiClient.get('/kb/hierarchy');
        // 兼容后端返回结构
        const items = res.data.data;
        const data = items.map((item: any, index: number) => ({
          title: typeof item === 'string' ? item : item.kb_name,
          key: typeof item === 'string' ? index + 1 : item.kb_id,
          isLeaf: typeof item === 'string' ? true : item.kb_type === 'FILE'
        }));
        setTreeData(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchHierarchy();
  }, []);

  if (loading) return <Spin size="small" style={{ margin: '20px' }} />;
  if (treeData.length === 0) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无挂载台账" />;

  return (
    <Tree
      checkable
      treeData={treeData}
      checkedKeys={context_kb_ids.map(id => String(id))}
      onCheck={(keys: any) => {
        const checkedKeys = keys.checked || keys;
        setContextKbIds(checkedKeys.map((k: string) => Number(k)));
      }}
      style={{ background: 'transparent' }}
    />
  );
};