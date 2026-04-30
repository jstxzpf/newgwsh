import enum
from typing import Optional, Any
from sqlalchemy import String, Enum, Integer, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base, TimestampMixin

class KbType(enum.Enum):
    DIRECTORY = "DIRECTORY"
    FILE = "FILE"

class KbTier(enum.Enum):
    BASE = "BASE"
    DEPT = "DEPT"
    PERSONAL = "PERSONAL"

class SecurityLevel(enum.IntEnum):
    GENERAL = 1
    IMPORTANT = 2
    CORE = 3

class KnowledgePhysicalFile(Base, TimestampMixin):
    """物理文件元数据表"""
    __tablename__ = "knowledge_physical_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_path: Mapped[str] = mapped_column(String(512), comment="物理存储路径")
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="SHA-256内容哈希")
    file_size: Mapped[int] = mapped_column(Integer, comment="文件大小(bytes)")
    mime_type: Mapped[str] = mapped_column(String(100), comment="MIME类型")
    security_level: Mapped[SecurityLevel] = mapped_column(
        Enum(SecurityLevel), 
        default=SecurityLevel.GENERAL,
        comment="安全等级"
    )

class KnowledgeBaseHierarchy(Base, TimestampMixin):
    """知识库层级结构表"""
    __tablename__ = "knowledge_base_hierarchy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kb_type: Mapped[KbType] = mapped_column(Enum(KbType), comment="节点类型")
    kb_tier: Mapped[KbTier] = mapped_column(Enum(KbTier), comment="库层级")
    name: Mapped[str] = mapped_column(String(255), comment="显示名称")
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("knowledge_base_hierarchy.id"), 
        nullable=True,
        comment="父节点ID"
    )
    physical_file_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("knowledge_physical_files.id"), 
        nullable=True,
        comment="关联物理文件"
    )
    owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="所有者ID")
    dept_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True, comment="部门ID")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否软删除")

    # 关系定义
    parent = relationship("KnowledgeBaseHierarchy", remote_side=[id], backref="children")
    physical_file = relationship("KnowledgePhysicalFile")

class KnowledgeChunk(Base, TimestampMixin):
    """知识分片表"""
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    kb_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("knowledge_base_hierarchy.id"), 
        index=True,
        comment="关联层级节点ID"
    )
    content: Mapped[str] = mapped_column(Text, comment="切片文本内容")
    embedding: Mapped[Any] = mapped_column(Vector(1024), comment="向量数据(1024维)")
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, name="metadata", nullable=True, comment="扩展元数据")

    kb_node = relationship("KnowledgeBaseHierarchy")
