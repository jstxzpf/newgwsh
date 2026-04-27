import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import select
from app.models.knowledge import KnowledgeBaseHierarchy, KnowledgeChunk, KnowledgePhysicalFile
from app.models.user import User
from app.core.enums import KBTier, DataSecurityLevel
from app.tasks.worker import parse_kb_file_task

@pytest.mark.asyncio
async def test_kb_parse_rollback_on_failure(db_session_factory):
    """
    TC-03: 验证知识库解析失败时的原子性与数据回滚。
    """
    async with db_session_factory() as db:
        user = User(username="kb_tester_final", password_hash="hash", role_level=1)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        phys_file = KnowledgePhysicalFile(content_hash="rollback_hash_final", file_path="/tmp/test.md")
        db.add(phys_file)
        await db.commit()
        await db.refresh(phys_file)

        kb_node = KnowledgeBaseHierarchy(
            kb_name="Final Atomic Test",
            kb_type="FILE",
            kb_tier=KBTier.PERSONAL,
            security_level=DataSecurityLevel.GENERAL,
            owner_id=user.user_id,
            physical_file_id=phys_file.file_id,
            parse_status="READY"
        )
        db.add(kb_node)
        await db.commit()
        await db.refresh(kb_node)
        kb_id = kb_node.kb_id

    # 运行任务并模拟崩溃
    # 注意：我们直接模拟内部引擎崩溃，观察 worker.py 中的异常处理逻辑是否生效
    with patch("app.tasks.worker.update_task_progress"), \
         patch("app.tasks.worker.MarkItDown") as mock_mid:
        
        # 强制抛出特定异常
        mock_mid.return_value.convert.side_effect = Exception("ATOMicity_CRASH_TEST")
        
        # 由于我们无法在测试中完美模拟 Celery 的 retry 机制，我们只需确保异常向上传播
        # 且内部的回滚代码已被执行
        with pytest.raises(Exception) as excinfo:
            # 传 2 个参数，让 Celery 自动注入 self
            parse_kb_file_task(kb_id, "/tmp/test.md")
        
        assert "ATOMicity_CRASH_TEST" in str(excinfo.value)

    # 【核心断言】验证原子性：数据库中不应有该 kb_id 的任何数据
    async with db_session_factory() as db:
        # 验证 1：脏切片必须为空
        res = await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.kb_id == kb_id))
        chunks = res.scalars().all()
        assert len(chunks) == 0, f"原子性校验失败：解析崩溃后残留了 {len(chunks)} 条脏数据"

        # 验证 2：状态必须已更新为 FAILED
        res_node = await db.execute(select(KnowledgeBaseHierarchy).where(KnowledgeBaseHierarchy.kb_id == kb_id))
        node = res_node.scalar_one()
        assert node.parse_status == "FAILED", f"状态更新校验失败：预期 FAILED，实际 {node.parse_status}"

    print(f"\n[TC-03 Success] 知识库解析原子性与回滚机制验证通过。")
