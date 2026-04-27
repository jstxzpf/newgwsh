import pytest
from app.models.user import User, Department
from app.models.document import Document
from app.api.dependencies import get_current_user
from app.main import app
from app.core.enums import DocumentStatus
from sqlalchemy import select

@pytest.fixture
def auth_override():
    """权限覆盖 Fixture：仅管理用户身份"""
    app.dependency_overrides.pop(get_current_user, None)
    yield app.dependency_overrides
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
async def setup_data(setup_infrastructure, db_session_factory):
    """准备测试基础数据：部门、起草人、审批人"""
    async with db_session_factory() as db:
        import uuid
        suffix = str(uuid.uuid4())[:8]
        dept = Department(dept_name=f"测试部_{suffix}", dept_code=f"TEST_{suffix}")
        db.add(dept)
        await db.commit()
        await db.refresh(dept)
        
        drafter = User(username=f"drafter_{suffix}", dept_id=dept.dept_id, role_level=1, password_hash="dummy")
        db.add(drafter)
        reviewer = User(username=f"reviewer_{suffix}", dept_id=dept.dept_id, role_level=5, password_hash="dummy")
        db.add(reviewer)
        
        await db.commit()
        await db.refresh(drafter)
        await db.refresh(reviewer)
        
        dept.dept_head_id = reviewer.user_id
        await db.commit()
        
        return {"dept": dept, "drafter": drafter, "reviewer": reviewer}

@pytest.mark.asyncio
async def test_full_document_lifecycle(client, setup_data, auth_override, db_session_factory):
    drafter = setup_data["drafter"]
    reviewer = setup_data["reviewer"]
    
    # 1. Init
    app.dependency_overrides[get_current_user] = lambda: drafter
    res = await client.post("/api/v1/documents/init", json={"title": "集成测试全链路公文"})
    assert res.status_code == 200
    doc_id = res.json()["doc_id"]
    
    # 2. Lock & Save
    res = await client.post(f"/api/v1/locks/acquire?doc_id={doc_id}")
    lock_token = res.json()["lock_token"]
    long_content = "这是一段足够长的公文正文，用于通过后端系统的长度有效性校验。这段话超过了二十个字。1234567890"
    res = await client.post(f"/api/v1/documents/{doc_id}/auto-save?lock_token={lock_token}", json={"content": long_content})
    assert res.status_code == 200
    
    # 3. Submit
    res = await client.post(f"/api/v1/documents/{doc_id}/submit")
    assert res.status_code == 200
    
    # 4. Review
    app.dependency_overrides[get_current_user] = lambda: reviewer
    res = await client.post(f"/api/v1/approval/{doc_id}/review", json={"is_approved": True})
    assert res.status_code == 200
    
    # 5. Check
    res = await client.get(f"/api/v1/documents/{doc_id}")
    assert res.json()["status"] == DocumentStatus.APPROVED.value

@pytest.mark.asyncio
async def test_security_and_permission_boundaries(client, setup_data, auth_override):
    drafter = setup_data["drafter"]
    reviewer = setup_data["reviewer"]
    
    # 1. Init
    app.dependency_overrides[get_current_user] = lambda: drafter
    res = await client.post("/api/v1/documents/init", json={"title": "安全测试公文"})
    doc_id = res.json()["doc_id"]
    
    # 2. Invalid Token
    res = await client.post(f"/api/v1/documents/{doc_id}/auto-save?lock_token=wrong", json={"content": "x"})
    assert res.status_code == 409 
    
    # 3. Valid Submit (Identity check)
    lock_res = await client.post(f"/api/v1/locks/acquire?doc_id={doc_id}")
    real_token = lock_res.json()["lock_token"]
    
    long_content = "这是一段足够长的公文正文，用于通过后端系统的长度有效性校验。这段话超过了二十个字。1234567890"
    await client.post(f"/api/v1/documents/{doc_id}/auto-save?lock_token={real_token}", json={"content": long_content})
    
    res = await client.post(f"/api/v1/documents/{doc_id}/submit")
    assert res.status_code == 200, f"Submit failed: {res.text}"
    
    # 4. Unauthorized Review
    app.dependency_overrides[get_current_user] = lambda: drafter
    res = await client.post(f"/api/v1/approval/{doc_id}/review", json={"is_approved": True})
    assert res.status_code == 403
    
    # 5. Authorized Review
    app.dependency_overrides[get_current_user] = lambda: reviewer
    res = await client.post(f"/api/v1/approval/{doc_id}/review", json={"is_approved": True})
    assert res.status_code == 200
