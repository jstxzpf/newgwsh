import React, { useEffect, useState } from 'react';
import { Drawer, List, Button, Popconfirm, message, Tag } from 'antd';
import { apiClient } from '../../../api/client';
import { useEditorStore } from '../../../stores/editorStore';

interface Snapshot {
  snapshot_id: number;
  content: string;
  trigger_event: string;
  created_at: string;
}

interface SnapshotRecoveryDrawerProps {
  open: boolean;
  onClose: () => void;
}

export const SnapshotRecoveryDrawer: React.FC<SnapshotRecoveryDrawerProps> = ({ open, onClose }) => {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const { currentDocId, setContent } = useEditorStore();

  const fetchSnapshots = async () => {
    if (!currentDocId) return;
    try {
      const res = await apiClient.get(`/documents/${currentDocId}/snapshots`, {
        params: { page: 1, page_size: 20 }
      });
      // 兼容扁平列表或分页结构
      const items = res.data.data.items || res.data.data;
      setSnapshots(items || []);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (open) fetchSnapshots();
  }, [open, currentDocId]);

  const handleRestore = async (snapshot: Snapshot) => {
    try {
      // 铁律 (§七.1)：恢复前先存一次当前快照
      await apiClient.post(`/documents/${currentDocId}/snapshots`, {
        content: useEditorStore.getState().content,
        trigger_event: 'before_restore'
      });

      await apiClient.post(`/documents/${currentDocId}/snapshots/${snapshot.snapshot_id}/restore`);
      setContent(snapshot.content);
      message.success('恢复成功');
      onClose();
    } catch (e) {
      message.error('恢复失败');
    }
  };

  return (
    <Drawer
      title="历史快照 (云端后悔药)"
      placement="right"
      onClose={onClose}
      open={open}
      width={400}
    >
      <List
        dataSource={snapshots}
        renderItem={(item) => (
          <List.Item
            actions={[
              <Popconfirm 
                title="确认恢复？" 
                description="这将会覆盖当前画板内容，操作前系统将自动为您备份当前版本。"
                onConfirm={() => handleRestore(item)}
              >
                <Button type="link">恢复</Button>
              </Popconfirm>
            ]}
          >
            <List.Item.Meta
              title={new Date(item.created_at).toLocaleString()}
              description={<Tag color="blue">{item.trigger_event}</Tag>}
            />
          </List.Item>
        )}
      />
    </Drawer>
  );
};