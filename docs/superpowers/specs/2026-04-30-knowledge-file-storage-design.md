# 物理文件存储与去重服务设计规格说明 (2026-04-30)

## 1. 目标
实现知识库物理文件的存储逻辑，包含内容去重、分级存储以及安全等级变更触发的重解析机制。

## 2. 核心组件

### 2.1 存储配置 (`app/core/config.py`)
- `STORAGE_ROOT`: 物理文件存储的根目录，默认为项目根目录下的 `data/storage`。

### 2.2 文件工具 (`app/core/file_utils.py`)
- `calculate_hash(file_content: bytes) -> str`: 
  - 算法：SHA-256。
  - 用途：生成内容的唯一标识，用于去重。
- `get_storage_path(content_hash: str, filename: str) -> str`:
  - 目录结构：`{hash[:2]}/{hash[2:4]}/`。
  - 文件名：`{hash}_{filename}`（保留原始文件名便于调试，但通过哈希前缀确保唯一性）。
  - 返回值：相对于 `STORAGE_ROOT` 的相对路径。

### 2.3 文件服务 (`app/services/knowledge_file.py`)
- `save_physical_file(db, file_content, filename, security_level)`:
  - **输入**: 数据库会话、文件二进制内容、文件名、安全等级枚举。
  - **逻辑**:
    1. 计算内容 SHA-256 哈希。
    2. 在 `knowledge_physical_files` 表中根据 `content_hash` 检索。
    3. **去重与等级逻辑**:
       - 若记录已存在：
         - 比较 `new_level` 与 `old_level`。
         - 若 `new_level > old_level`：返回特殊信号（如 `"REPARSE_NEEDED"`），由调用方决定后续操作。
         - 若 `new_level <= old_level`：直接返回已有的 `phys_id`。
       - 若记录不存在：
         - 调用 `file_utils` 获取存储路径。
         - 确保物理目录存在，将内容写入磁盘。
         - 在数据库中创建新记录（存储相对路径、哈希、大小、MIME、安全等级）。
         - 返回新记录的 `id`。

## 3. 错误处理
- 磁盘写入失败：捕获 I/O 异常，记录日志并向上抛出，确保数据库事务回滚（如果涉及）。
- 数据库唯一约束冲突：虽然前置检查已规避，但在高并发下可能出现。需捕获 `IntegrityError` 并重新查询。

## 4. 测试与验证
- 单元测试：
  - 相同内容文件上传：验证返回相同的 ID，且磁盘文件不重复写入。
  - 等级提升上传：验证返回重解析信号。
  - 路径生成算法：验证生成的路径符合 `ab/cd/hash_name` 格式。
- 集成测试：
  - 模拟 API 调用全流程。
