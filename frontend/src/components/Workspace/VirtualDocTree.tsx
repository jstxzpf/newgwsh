import React, { useEffect, useState } from 'react';
import { Tree, message, Spin } from 'antd';
import type { TreeDataNode } from 'antd';
import { useEditorStore } from '../../store/useEditorStore';
import apiClient from '../../api/client';
import { appConfig } from '../../config';

export const VirtualDocTree: React.FC = () => {
  const [treeData, setTreeData] = useState<TreeDataNode[]>([]);
  const [loading, setLoading] = useState(false);
  const { context_kb_ids, setContextKbIds } = useEditorStore();

  useEffect(() => {
    const fetchTree = async () => {
      setLoading(true);
      try {
        const res = await apiClient.get('/kb/hierarchy');
        // 简单转换为 AntD Tree 格式
        const nodes = res.data.map((item: any) => ({
          title: item.kb_name,
          key: item.kb_id.toString(), // Tree 要求 key 为 string
          isLeaf: item.kb_type === 'FILE',
          disabled: item.kb_type === 'FILE' && item.parse_status !== 'READY',
        }));
        setTreeData(nodes);
      } catch (e) {
        message.error('无法拉取台账目录');
      } finally {
        setLoading(false);
      }
    };
    fetchTree();
  }, []);

  const onCheck = (checkedKeys: any) => {
    // 提取数字 ID
    const ids = checkedKeys.map((k: string) => parseInt(k, 10)).filter((k: number) => !isNaN(k));
    setContextKbIds(ids);
  };

  if (loading) return <div style={{ padding: '20px', textAlign: 'center' }}><Spin tip="加载目录树..." /></div>;

  return (
    <div style={{ padding: '16px', height: '100%', overflowY: 'auto' }}>
      <div style={{ marginBottom: '12px', fontWeight: 'bold', color: '#003366', fontSize: '14px' }}>
        📎 挂载统计台账上下文
      </div>
      <div style={{ fontSize: '12px', color: '#888', marginBottom: '16px' }}>
        勾选的文件将作为 AI 润色与问答的限定检索边界。
      </div>
      <Tree
        checkable
        treeData={treeData}
        checkedKeys={context_kb_ids.map(String)}
        onCheck={onCheck}
        style={{
          width: '100%',
          overflow: 'hidden'
        }}
        titleRender={(nodeData) => (
          <div 
            style={{ 
              minWidth: 0, 
              textOverflow: 'ellipsis', 
              whiteSpace: 'nowrap', 
              overflow: 'hidden',
              display: 'inline-block',
              maxWidth: appConfig.virtualTreeMaxWidth, // 颗粒度对齐：强制截断保护
              verticalAlign: 'middle'
            }} 
            title={nodeData.title as string}
          >
            {nodeData.title as React.ReactNode}
          </div>
        )}
      />
    </div>
  );
};
