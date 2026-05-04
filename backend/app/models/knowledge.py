from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, BigInt, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.models.enums import KBTier, DataSecurityLevel, KBTypeEnum
from datetime import datetime

class KnowledgePhysicalFile(Base):
    __tablename__ = "knowledge_physical_files"
    file_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInt, nullable=True)
    created_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    nodes = relationship("KnowledgeBaseHierarchy", back_populates="physical_file")
    chunks = relationship("KnowledgeChunk", back_populates="physical_file")

class KnowledgeBaseHierarchy(Base):
    __tablename__ = "knowledge_base_hierarchy"
    kb_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), index=True, nullable=True)
    kb_name: Mapped[str] = mapped_column(String(255), nullable=False)
    kb_type: Mapped[KBTypeEnum] = mapped_column(SQLEnum(KBTypeEnum), nullable=False)
    kb_tier: Mapped[KBTier] = mapped_column(SQLEnum(KBTier), nullable=False, default=KBTier.PERSONAL)
    dept_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=True)
    security_level: Mapped[DataSecurityLevel] = mapped_column(SQLEnum(DataSecurityLevel), nullable=False, default=DataSecurityLevel.GENERAL)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UPLOADED")
    physical_file_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("knowledge_physical_files.file_id"), index=True, nullable=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("KnowledgeBaseHierarchy", remote_side=[kb_id], backref="children")
    physical_file = relationship("KnowledgePhysicalFile", back_populates="nodes")
    owner = relationship("SystemUser")
    dept = relationship("Department")
    chunks = relationship("KnowledgeChunk", back_populates="kb_node", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    chunk_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), index=True, nullable=False)
    physical_file_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_physical_files.file_id"), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector | None] = mapped_column(Vector(1024), nullable=True) # 使用 bge-m3 1024维向量
    is_deleted: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False, default=False)
    kb_tier: Mapped[KBTier] = mapped_column(SQLEnum(KBTier), nullable=False)
    security_level: Mapped[DataSecurityLevel] = mapped_column(SQLEnum(DataSecurityLevel), nullable=False)
    dept_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=True)
    owner_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})

    # Relationships
    kb_node = relationship("KnowledgeBaseHierarchy", back_populates="chunks")
    physical_file = relationship("KnowledgePhysicalFile", back_populates="chunks")

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, BigInt, Index, Computed
...
    # 显式 HNSW 索引声明 (Task 4)
    __table_args__ = (
        Index(
            "idx_chunk_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where=(is_deleted == False), # 对齐索引优化建议 §四.1
        ),
        Index(
            "idx_chunk_content_gin",
            func.to_tsvector('zh', content),
            postgresql_using="gin",
            postgresql_where=(is_deleted == False), # 对齐索引优化建议 §四.2
        ),
        Index(
            "idx_chunk_metadata_gin",
            metadata_json,
            postgresql_using="gin", # 对齐索引优化建议 §四.3
        ),
    )