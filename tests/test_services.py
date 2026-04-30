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
