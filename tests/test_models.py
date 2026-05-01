import pytest
from sqlalchemy import select
from app.models.document import Document, DocStatus
from app.models.org import SystemUser, Department
from app.models.config import DocumentType

@pytest.mark.asyncio
async def test_create_document(db_session):
    # 1. 准备依赖数据
    dept = Department(dept_name="测试科室", dept_code="TEST01")
    db_session.add(dept)
    await db_session.flush()
    
    user = SystemUser(
        username="test_user", 
        full_name="测试用户", 
        password_hash="...", 
        dept_id=dept.dept_id
    )
    db_session.add(user)
    
    dt = DocumentType(type_code="NOTICE", type_name="通知")
    db_session.add(dt)
    await db_session.flush()

    # 2. 创建公文
    doc = Document(
        title="测试公文",
        doc_type_id=dt.type_id,
        creator_id=user.user_id,
        dept_id=dept.dept_id,
        status=DocStatus.DRAFTING
    )
    db_session.add(doc)
    await db_session.commit()
    
    # 3. 验证
    assert doc.doc_id is not None
    assert isinstance(doc.doc_id, str) # UUID 验证
    assert doc.status == DocStatus.DRAFTING

@pytest.mark.asyncio
async def test_document_status_machine(db_session):
    # 准备基础数据
    dept = Department(dept_name="机要室", dept_code="JY01")
    db_session.add(dept)
    await db_session.flush()
    user = SystemUser(username="signer", full_name="签批人", password_hash="...", dept_id=dept.dept_id)
    db_session.add(user)
    dt = DocumentType(type_code="REPORT", type_name="报告")
    db_session.add(dt)
    await db_session.flush()

    doc = Document(title="流转测试", doc_type_id=dt.type_id, creator_id=user.user_id, dept_id=dept.dept_id)
    db_session.add(doc)
    await db_session.flush()

    # 合法转换: DRAFTING -> SUBMITTED
    doc.status = DocStatus.SUBMITTED
    await db_session.flush()
    
    # 非法转换: SUBMITTED -> DRAFTING (应当抛出 ValueError)
    with pytest.raises(ValueError, match="Illegal status transition"):
        doc.status = DocStatus.DRAFTING
