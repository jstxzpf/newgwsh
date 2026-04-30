# 知识库资产管理设计规格说明 (Knowledge Asset Management Design Spec)

## 1. 概览
本设计旨在构建系统的统计知识中枢，支持多模态数据（Word, PDF, Excel, Zip）的摄入、解析、存储与检索。核心采用物理与逻辑分离的存储模型，通过 SHA-256 去重，并支持递归虚拟目录树。

## 2. 数据模型 (Data Model)

### 2.1 物理文件表 (`knowledge_physical_files`)
- **职能**: 存储磁盘上的真实文件记录。
- **关键字段**:
  - `content_hash`: SHA-256 唯一索引。
  - `file_path`: 宿主机存储路径。
  - `security_level`: 最高安全等级标记。

### 2.2 虚拟层级表 (`knowledge_base_hierarchy`)
- **职能**: 管理用户可见的目录树。
- **关键字段**:
  - `kb_type`: `DIRECTORY` 或 `FILE`。
  - `kb_tier`: `BASE` (全局), `DEPT` (科室), `PERSONAL` (个人)。
  - `parent_id`: 指向父节点（支持无限级）。
  - `physical_file_id`: 若为 `FILE` 则关联物理表。
  - `is_deleted`: 软删除标记。

### 2.3 向量切片表 (`knowledge_chunks`)
- **职能**: 存储解析后的语义块。
- **字段**: `id`, `kb_id`, `content`, `embedding` (1024D), `metadata` (含标题路径、表头信息)。

## 3. 解析流水线 (Parsing Pipeline)

### 3.1 物理去重逻辑
- 上传时计算哈希。
- 若哈希命中且新上传的安全等级 $\le$ 已有等级，复用物理记录。
- 若新安全等级更高，则**强制重新存储并解析**，以隔离不同等级的算力处理。

### 3.2 异步解析任务 (`PARSE`)
- **MarkItDown**: 提取富文本。
- **AST 切片**: 使用 `markdown-it-py`。
- **锚点注入**: 每个切片必须包含从根目录到该文件的完整“标题路径”元数据。
- **压缩包处理**: 递归解压并自动在 `knowledge_base_hierarchy` 创建对应的 `DIRECTORY` 节点。

## 4. 权限与安全 (Auth & Security)

### 4.1 访问控制
- **BASE**: `Role >= USER` 只读，`Role == ADMIN` 可写。
- **DEPT**: `dept_id` 匹配可见。
- **PERSONAL**: `owner_id` 匹配可见。

### 4.2 级联软删除
- 使用 `WITH RECURSIVE` 递归标记子树 `is_deleted = True`。
- **副作用**: 必须同步清空对应 Chunks 的检索索引（向量检索时强制 `JOIN is_deleted = False`）。

## 5. 存储策略
- **物理存储**: Docker 卷挂载路径（宿主机 `uploads/`）。
- **去重路径**: 文件按哈希值前两位分级存储（如 `uploads/ab/cd...`），防止单目录下文件过多。
