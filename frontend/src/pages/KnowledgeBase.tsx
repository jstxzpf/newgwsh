import React, { useState } from 'react';
import { Layout, Table, Tag, Space, Button, Card, Tabs, Upload, Input, Tree } from 'antd';
import {
  FolderOutlined,
  FileOutlined,
  UploadOutlined,
  SearchOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
} from '@ant-design/icons';

const { Sider, Content } = Layout;

const KnowledgeBase: React.FC = () => {
  const [activeTab, setActiveTab] = useState('personal');

  const columns = [
    { title: '资产名称', dataIndex: 'name', key: 'name', render: (text: string, record: any) => (
      <span>{record.type === 'folder' ? <FolderOutlined style={{ marginRight: 8, color: '#1890ff' }} /> : <FileOutlined style={{ marginRight: 8 }} />}{text}</span>
    )},
    { title: '安全等级', dataIndex: 'security', key: 'security', render: (level: string) => {
      let color = 'green';
      if (level === '核心') color = 'red';
      if (level === '重要') color = 'orange';
      return <Tag color={color}>{level}</Tag>;
    }},
    { title: '解析状态', dataIndex: 'status', key: 'status', render: (status: string) => (
      <Tag color={status === 'READY' ? 'success' : 'processing'}>{status}</Tag>
    )},
    { title: '上传者', dataIndex: 'owner', key: 'owner' },
    { title: '更新时间', dataIndex: 'updatedAt', key: 'updatedAt' },
    { title: '操作', key: 'action', render: () => (
      <Space size="middle">
        <Button type="link" icon={<EyeOutlined />}>预览</Button>
        <Button type="link" icon={<ReloadOutlined />}>替换</Button>
        <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
      </Space>
    )},
  ];

  const data = [
    { key: '1', name: '2024年一季度调研数据', type: 'file', security: '重要', status: 'READY', owner: '系统管理员', updatedAt: '2026-05-01 09:00' },
    { key: '2', name: '往期台账备份', type: 'folder', security: '一般', status: 'READY', owner: '系统管理员', updatedAt: '2026-04-20 15:30' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            { key: 'personal', label: '个人沙箱库' },
            { key: 'dept', label: '科室共享库' },
            { key: 'base', label: '全局基础库' },
            { key: 'exemplar', label: '参考范文' },
          ]}
        />
        
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Space>
            <Input placeholder="搜索资源..." prefix={<SearchOutlined />} style={{ width: 250 }} />
            <Button icon={<ReloadOutlined />}>刷新</Button>
          </Space>
          <Upload showUploadList={false}>
            <Button type="primary" icon={<UploadOutlined />}>上传文件 / 文件夹</Button>
          </Upload>
        </div>

        {activeTab === 'exemplar' ? (
          <Table
            columns={[
              { title: '范文标题', dataIndex: 'title', key: 'title' },
              { title: '关联文种', dataIndex: 'type', key: 'type', render: (text: string) => <Tag color="blue">{text}</Tag> },
              { title: '上传者', dataIndex: 'owner', key: 'owner' },
              { title: '操作', key: 'action', render: () => (
                <Space>
                  <Button type="link">预览文本</Button>
                  <Button type="link" danger>删除</Button>
                </Space>
              )},
            ]}
            dataSource={[
              { key: '1', title: '2024年调查报告标准范文', type: '调研分析', owner: '系统管理员' },
            ]}
          />
        ) : (
          <Layout style={{ background: '#fff' }}>
            <Sider width={200} theme="light" style={{ background: '#f9f9f9' }}>
              <Tree
                showIcon
                defaultExpandAll
                treeData={[
                  { title: '所有资源', key: 'root', icon: <FolderOutlined />, children: [
                    { title: '2024年度', key: '2024', icon: <FolderOutlined /> },
                    { title: '法律法规', key: 'law', icon: <FolderOutlined /> },
                  ]}
                ]}
              />
            </Sider>
            <Content style={{ paddingLeft: 16 }}>
              <Table columns={columns} dataSource={data} />
            </Content>
          </Layout>
        )}
      </Card>
    </div>
  );
};

export default KnowledgeBase;
