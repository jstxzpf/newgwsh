import pytest
from app.models.document import Document, DocStatus
from app.models.audit import WorkflowAudit, DocumentApprovalLog

def test_document_status_transitions():
    doc = Document(title="Test Doc", creator_id=1)
    assert doc.status == DocStatus.DRAFTING

    # 合法转换: DRAFTING -> SUBMITTED
    doc.status = DocStatus.SUBMITTED
    assert doc.status == DocStatus.SUBMITTED

    # 合法转换: SUBMITTED -> REJECTED
    doc.status = DocStatus.REJECTED
    assert doc.status == DocStatus.REJECTED

    # 合法转换: REJECTED -> DRAFTING
    doc.status = DocStatus.DRAFTING
    assert doc.status == DocStatus.DRAFTING

    # 合法转换: DRAFTING -> SUBMITTED -> APPROVED
    doc.status = DocStatus.SUBMITTED
    doc.status = DocStatus.APPROVED
    assert doc.status == DocStatus.APPROVED

    # 非法转换: APPROVED -> DRAFTING (终态不可逆)
    with pytest.raises(ValueError) as excinfo:
        doc.status = DocStatus.DRAFTING
    assert "Invalid status transition from APPROVED to DRAFTING" in str(excinfo.value)

    # 非法转换: SUBMITTED -> DRAFTING (必须先驳回)
    doc_new = Document(title="New Doc", creator_id=1, status=DocStatus.SUBMITTED)
    with pytest.raises(ValueError) as excinfo:
        doc_new.status = DocStatus.DRAFTING
    assert "Invalid status transition from SUBMITTED to DRAFTING" in str(excinfo.value)

def test_timestamp_mixin():
    doc = Document(title="Timestamp Test", creator_id=1)
    # created_at 和 updated_at 在落库前可能是 None，但在模型实例化时通过 mixin 定义了。
    # 这里主要验证字段是否存在。
    assert hasattr(doc, "created_at")
    assert hasattr(doc, "updated_at")

def test_workflow_audit_model():
    audit = WorkflowAudit(
        doc_id=1,
        operator_id=2,
        action="SUBMIT",
        from_status=DocStatus.DRAFTING,
        to_status=DocStatus.SUBMITTED,
        reason="Looks good",
        trace_id="trace-123"
    )
    assert audit.doc_id == 1
    assert audit.operator_id == 2
    assert audit.action == "SUBMIT"
    assert audit.from_status == DocStatus.DRAFTING
    assert audit.to_status == DocStatus.SUBMITTED
    assert audit.reason == "Looks good"
    assert audit.trace_id == "trace-123"
    assert hasattr(audit, "created_at")

from app.models.knowledge import (
    KnowledgePhysicalFile, KnowledgeBaseHierarchy, KnowledgeChunk,
    KbType, KbTier, SecurityLevel
)
import numpy as np

def test_knowledge_models():
    # 1. 物理文件测试
    phys = KnowledgePhysicalFile(
        file_path="uploads/test.pdf",
        content_hash="hash123",
        file_size=1024,
        mime_type="application/pdf",
        security_level=SecurityLevel.IMPORTANT
    )
    assert phys.content_hash == "hash123"
    assert phys.security_level == SecurityLevel.IMPORTANT

    # 2. 层级结构测试
    folder = KnowledgeBaseHierarchy(
        kb_type=KbType.DIRECTORY,
        kb_tier=KbTier.BASE,
        name="Root Folder"
    )
    assert folder.kb_type == KbType.DIRECTORY
    
    file_node = KnowledgeBaseHierarchy(
        kb_type=KbType.FILE,
        kb_tier=KbTier.BASE,
        name="Test File",
        parent=folder,
        physical_file=phys
    )
    assert file_node.parent.name == "Root Folder"
    assert file_node.physical_file.content_hash == "hash123"

    # 3. 切片测试 (Vector 实例化)
    vec = np.random.rand(1024).tolist()
    chunk = KnowledgeChunk(
        kb_id=1,
        content="This is a test chunk",
        embedding=vec,
        metadata_json={"page": 1}
    )
    assert len(chunk.embedding) == 1024
    assert chunk.metadata_json["page"] == 1
