import React, { useState } from 'react';
import { Drawer, List, Button, Popconfirm, message } from 'antd';
import { HistoryOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';
import { useEditorStore } from '../../store/useEditorStore';

interface Props {
  docId: string | null;
}

export const SnapshotRecoveryDrawer: React.FC<Props> = ({ docId }) => {
  const [visible, setVisible] = useState(false);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const { setContent } = useEditorStore();

  const fetchSnapshots = async () => {
    if (!docId) return;
    try {
      const res = await apiClient.get(`/documents/${docId}/snapshots`, {
        params: { page: 1, page_size: 20 }
      });
      setSnapshots(res.data.data);
    } catch (e) {
      message.error('拉取快照失败');
    }
  };

  const handleOpen = () => {
    setVisible(true);
    fetchSnapshots();
  };

  const handleRestore = async (id: number, content: string) => {
    if (!docId) return;
    try {
      // 【对齐修复】增加二次确认参数
      await apiClient.post(`/documents/${docId}/snapshots/${id}/restore?confirm=CONFIRMED`);
      setContent(content);
      message.success(`快照 #${id} 内容已恢复至当前画板`);
      setVisible(false);
    } catch (e) {
      message.error('云端恢复失败，请稍后重试');
    }
  };

  return (
    <>
      <Button icon={<HistoryOutlined />} onClick={handleOpen}>历史快照 ⏱</Button>
      <Drawer
        title="历史快照备份 (Cloud History)"
        placement="right"
        onClose={() => setVisible(false)}
        open={visible}
        width={350}
      >
        <div style={{ marginBottom: 16, fontSize: 12, color: '#888' }}>
          提示: 恢复快照将覆盖当前正在编辑的内容。系统已为您自动在覆盖前创建了最新备份。
        </div>
        <List
          dataSource={snapshots}
          renderItem={item => (
            <List.Item actions={[
              <Popconfirm title="确定覆盖当前画板吗？" onConfirm={() => handleRestore(item.snapshot_id || item.id, item.content)}>
                <Button type="link" size="small">恢复</Button>
              </Popconfirm>
            ]}>
              <List.Item.Meta
                title={`快照 #${item.id}`}
                description={<>
                  <div>时间: {new Date(item.created_at).toLocaleString()}</div>
                  <div>动作: <span style={{ color: '#003366' }}>{item.trigger_event}</span></div>
                </>}
              />
            </List.Item>
          )}
        />
      </Drawer>
    </>
  );
};
