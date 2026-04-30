import pytest
from app.services.knowledge_file import KnowledgeFileService
from app.models.knowledge import SecurityLevel, KnowledgePhysicalFile
from app.core.config import settings
import os
import shutil

@pytest.mark.asyncio
async def test_save_physical_file_deduplication(db_session):
    # 准备测试数据
    content = b"hello world"
    filename = "test.txt"
    
    # 1. 首次上传
    phys_id_1, needs_reparse_1 = await KnowledgeFileService.save_physical_file(
        db_session, content, filename, SecurityLevel.GENERAL
    )
    assert needs_reparse_1 is True
    
    # 2. 重复上传（同等级）
    phys_id_2, needs_reparse_2 = await KnowledgeFileService.save_physical_file(
        db_session, content, filename, SecurityLevel.GENERAL
    )
    assert phys_id_1 == phys_id_2
    assert needs_reparse_2 is False
    
    # 3. 重复上传（更高等级）
    phys_id_3, needs_reparse_3 = await KnowledgeFileService.save_physical_file(
        db_session, content, filename, SecurityLevel.CORE
    )
    assert phys_id_1 == phys_id_3
    assert needs_reparse_3 is True
    
    # 检查数据库更新
    from sqlalchemy import select
    res = await db_session.execute(select(KnowledgePhysicalFile).where(KnowledgePhysicalFile.id == phys_id_1))
    phys = res.scalar_one()
    assert phys.security_level == SecurityLevel.CORE

    # 清理
    storage_path = os.path.join(settings.STORAGE_ROOT, phys.file_path)
    if os.path.exists(os.path.dirname(storage_path)):
        # 注意：这里我们只删除测试产生的目录
        pass 

from app.services.knowledge_hierarchy import KnowledgeHierarchyService
from app.models.knowledge import KnowledgeBaseHierarchy, KbType, KbTier, KnowledgeChunk
import numpy as np

@pytest.mark.asyncio
async def test_recursive_soft_delete(db_session):
    # 1. 构建目录树
    root = await KnowledgeHierarchyService.create_node(
        db_session, "Root", KbType.DIRECTORY, KbTier.BASE
    )
    sub = await KnowledgeHierarchyService.create_node(
        db_session, "Sub", KbType.DIRECTORY, KbTier.BASE, parent_id=root.id
    )
    file = await KnowledgeHierarchyService.create_node(
        db_session, "File", KbType.FILE, KbTier.BASE, parent_id=sub.id
    )
    
    # 2. 为文件添加切片
    chunk = KnowledgeChunk(
        kb_id=file.id,
        content="test content",
        embedding=np.random.rand(1024).tolist()
    )
    db_session.add(chunk)
    await db_session.commit()
    
    # 3. 执行递归删除
    await KnowledgeHierarchyService.soft_delete_subtree(db_session, root.id)
    
    # 4. 验证
    from sqlalchemy import select
    # 检查目录
    res = await db_session.execute(select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.id == root.id))
    assert res.scalar_one().is_deleted is True
    
    res_sub = await db_session.execute(select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.id == sub.id))
    assert res_sub.scalar_one().is_deleted is True
    
    res_file = await db_session.execute(select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.id == file.id))
    assert res_file.scalar_one().is_deleted is True
    
    # 检查切片
    res_chunk = await db_session.execute(select(KnowledgeChunk).where(KnowledgeChunk.kb_id == file.id))
    assert res_chunk.scalar_one().is_deleted is True
