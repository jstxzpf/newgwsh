# 物理文件存储与去重服务实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现物理文件存储与去重逻辑，确保相同内容仅存储一份，并处理安全等级变更。

**架构：** 在 `app/core/file_utils.py` 实现底层哈希与路径计算，在 `app/services/knowledge_file.py` 封装业务逻辑。使用 `data/storage` 作为默认根目录。

**技术栈：** Python, SQLAlchemy (Async), SHA-256.

---

### 任务 1：配置与工具层实现

**文件：**
- 修改：`app/core/config.py`
- 创建：`app/core/file_utils.py`

- [ ] **步骤 1：修改 `app/core/config.py` 添加 `STORAGE_ROOT`**

```python
# 在 Settings 类中添加
    STORAGE_ROOT: str = "data/storage"
```

- [ ] **步骤 2：创建 `app/core/file_utils.py` 并实现哈希与路径逻辑**

```python
import hashlib
import os

def calculate_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()

def get_storage_path(content_hash: str, filename: str) -> str:
    # subdirs: ab/cd/
    sub1 = content_hash[:2]
    sub2 = content_hash[2:4]
    # safe filename: {hash}_{original_name}
    # 简单的清理文件名中的特殊字符（可选，此处保持简单）
    safe_name = f"{content_hash}_{filename}"
    return os.path.join(sub1, sub2, safe_name)
```

- [ ] **步骤 3：Commit**

```bash
git add app/core/config.py app/core/file_utils.py
git commit -m "feat: add storage config and file utilities"
```

---

### 任务 2：存储服务逻辑实现

**文件：**
- 创建：`app/services/knowledge_file.py`

- [ ] **步骤 1：实现 `save_physical_file` 异步函数**

```python
import os
import aiofiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.file_utils import calculate_hash, get_storage_path
from app.models.knowledge import KnowledgePhysicalFile, SecurityLevel

async def save_physical_file(
    db: AsyncSession, 
    file_content: bytes, 
    filename: str, 
    security_level: SecurityLevel
) -> int | str:
    content_hash = calculate_hash(file_content)
    
    # 1. 检查哈希是否存在
    result = await db.execute(
        select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.content_hash == content_hash)
    )
    existing_file = result.scalar_one_or_none()
    
    if existing_file:
        # 去重逻辑
        if security_level > existing_file.security_level:
            return "REPARSE_NEEDED"
        return existing_file.id
    
    # 2. 写入物理文件
    rel_path = get_storage_path(content_hash, filename)
    full_path = os.path.join(settings.STORAGE_ROOT, rel_path)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # 异步写入
    async with aiofiles.open(full_path, mode="wb") as f:
        await f.write(file_content)
    
    # 3. 写入数据库
    new_file = KnowledgePhysicalFile(
        file_path=rel_path,
        content_hash=content_hash,
        file_size=len(file_content),
        mime_type="application/octet-stream", # 简化处理，实际可根据 filename 扩展
        security_level=security_level
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)
    
    return new_file.id
```

- [ ] **步骤 2：Commit**

```bash
git add app/services/knowledge_file.py
git commit -m "feat: implement physical file storage service with deduplication"
```

---

### 任务 3：验证与测试

**文件：**
- 创建：`tests/test_storage_service.py`

- [ ] **步骤 1：编写测试用例覆盖去重和等级变更**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.knowledge_file import save_physical_file
from app.models.knowledge import SecurityLevel
from app.core.config import settings
import os
import shutil

@pytest.mark.asyncio
async def test_deduplication_logic(db_session: AsyncSession):
    content = b"hello world"
    name = "test.txt"
    
    # 1. 第一次上传
    id1 = await save_physical_file(db_session, content, name, SecurityLevel.GENERAL)
    assert isinstance(id1, int)
    
    # 2. 第二次上传相同内容，相同等级 -> 返回相同ID
    id2 = await save_physical_file(db_session, content, name, SecurityLevel.GENERAL)
    assert id1 == id2
    
    # 3. 第三次上传相同内容，更高等级 -> 返回 REPARSE_NEEDED
    res = await save_physical_file(db_session, content, name, SecurityLevel.CORE)
    assert res == "REPARSE_NEEDED"

    # 4. 上传不同内容 -> 不同ID
    id3 = await save_physical_file(db_session, b"different content", name, SecurityLevel.GENERAL)
    assert id3 != id1
```

- [ ] **步骤 2：运行测试验证**

运行：`pytest tests/test_storage_service.py`

- [ ] **步骤 3：清理测试产生的物理文件 (可选)**

---

### 任务 4：完成报告

- [ ] **步骤 1：列出所有创建的文件内容并宣布 DONE**
