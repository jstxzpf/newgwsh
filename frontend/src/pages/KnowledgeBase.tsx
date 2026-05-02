import React, { useState, useEffect, useMemo } from 'react';
import { Layout, Table, Tag, Space, Button, Tabs, Upload, Input, Tree, Typography, theme, message, Modal } from 'antd';
import {
  FolderOutlined,
  FileOutlined,
  UploadOutlined,
  SearchOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { kbService, KBResource } from '../api/services';

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

const KnowledgeBase: React.FC = () => {
  const { token } = theme.useToken();
  const [activeTab, setActiveTab] = useState('personal');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<KBResource[]>([]);
  const [treeData, setTreeData] = useState<any[]>([]);

  // [P1] harden: 加载真实数据
  const fetchData = async () => {
    setLoading(true);
    try {
      // [P0] harden: 由于拦截器已解构 res.data，直接使用 res
      const res = await kbService.getHierarchy();
      setTreeData(res || []);
      
      // 模拟当前选中的文件列表
      setData([
        { key: '1', name: '2024年一季度调研数据', type: 'file', security: '重要', status: 'READY', owner: '系统管理员', updatedAt: '2026-05-01 09:00' },
        { key: '2', name: '往期台账备份', type: 'folder', security: '一般', status: 'READY', owner: '系统管理员', updatedAt: '2026-04-20 15:30' },
      ]);
    } catch (error) {
      console.error('KB Fetch Error:', error);
      message.error('无法连接到知识资产中枢');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  // [P2] optimize: columns 定义
  const columns = useMemo(() => [
    { 
      title: '资产名称', 
      dataIndex: 'name', 
      key: 'name', 
      render: (text: string, record: KBResource) => (
        <Space>
          {record.type === 'folder' ? 
            <FolderOutlined style={{ color: token.colorPrimary }} /> : 
            <FileOutlined style={{ color: token.colorTextDescription }} />
          }
          <Text strong={record.type === 'folder'}>{text}</Text>
        </Space>
      )
    },
    { 
      title: '安全等级', 
      dataIndex: 'security', 
      key: 'security', 
      render: (level: string) => {
        let color = 'success';
        if (level === '核心') color = 'error';
        if (level === '重要') color = 'warning';
        return <Tag color={color}>{level}</Tag>;
      }
    },
    { 
      title: '解析状态', 
      dataIndex: 'status', 
      key: 'status', 
      render: (status: string) => (
        <Tag bordered={false} color={status === 'READY' ? 'success' : 'processing'}>
          {status === 'READY' ? '就绪' : '解析中'}
        </Tag>
      )
    },
    { title: '更新时间', dataIndex: 'updatedAt', key: 'updatedAt' },
    { 
      title: '操作', 
      key: 'action', 
      render: (_: any, record: KBResource) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />}>预览</Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>卸载</Button>
        </Space>
      )
    },
  ], [token]);

  return (
    // [P0] layout: 引入“权威长卷”容器，提升呼吸感 (40px)
    <div style={{ padding: 40, backgroundColor: token.colorBgLayout, minHeight: '100%' }}>
      <div style={{ 
        maxWidth: 1200, 
        margin: '0 auto', 
        backgroundColor: token.colorBgContainer,
        borderRadius: token.borderRadiusSM,
        // [P2] polish: 提升阴影浓度至 0.1 实体感
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        padding: token.paddingLG
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: token.marginLG }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>知识资产中心</Title>
            <Text type="secondary">维护调查队权威知识资产，为 AI 提供精准语料支撑</Text>
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新同步</Button>
            <Upload showUploadList={false}>
              <Button type="primary" icon={<UploadOutlined />}>上传知识资产</Button>
            </Upload>
          </Space>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{ marginBottom: token.marginLG }}
          items={[
            { key: 'personal', label: '个人沙箱' },
            { key: 'dept', label: '科室共享' },
            { key: 'base', label: '全局法规' },
            { key: 'exemplar', label: '参考范文' },
          ]}
        />

        <Layout style={{ background: token.colorBgContainer }}>
          {/* [P1] colorize: 修正 Sider 与 Tree 的视觉表现 */}
          <Sider 
            width={240} 
            style={{ 
              background: token.colorFillQuaternary, 
              borderRadius: token.borderRadiusSM,
              padding: token.paddingSM,
              marginRight: token.marginLG
            }}
          >
            <div style={{ marginBottom: token.marginSM, padding: '0 8px' }}>
              <Input placeholder="检索目录..." prefix={<SearchOutlined />} variant="borderless" />
            </div>
            <Tree
              showIcon
              blockNode
              defaultExpandAll
              style={{ background: 'transparent' }}
              treeData={treeData.length > 0 ? treeData : [
                { title: '所有资源', key: 'root', icon: <DatabaseOutlined />, children: [
                  { title: '2024年度', key: '2024', icon: <FolderOutlined /> },
                  { title: '法律法规', key: 'law', icon: <FolderOutlined /> },
                ]}
              ]}
            />
          </Sider>
          <Content>
            <Table 
              columns={columns} 
              dataSource={data} 
              loading={loading}
              size="middle"
              pagination={{ pageSize: 8 }}
            />
          </Content>
        </Layout>
      </div>
    </div>
  );
};

export default KnowledgeBase;
