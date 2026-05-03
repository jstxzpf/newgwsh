from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, BigInt
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.models.enums import KBTier, DataSecurityLevel

class KnowledgePhysicalFile(Base):
    __tablename__ = "knowledge_physical_files"
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInt, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class KnowledgeBaseHierarchy(Base):
    __tablename__ = "knowledge_base_hierarchy"
    kb_id = Column(Integer, primary_key=True, autoincrement=True)
    parent_id = Column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), index=True, nullable=True)
    kb_name = Column(String(255), nullable=False)
    kb_type = Column(String(32), nullable=False)
    kb_tier = Column(SQLEnum(KBTier), nullable=False, default=KBTier.PERSONAL)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=True)
    security_level = Column(SQLEnum(DataSecurityLevel), nullable=False, default=DataSecurityLevel.GENERAL)
    parse_status = Column(String(32), nullable=False, default="UPLOADED")
    physical_file_id = Column(Integer, ForeignKey("knowledge_physical_files.file_id"), index=True, nullable=True)
    owner_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    chunk_id = Column(Integer, primary_key=True, autoincrement=True)
    kb_id = Column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), index=True, nullable=False)
    physical_file_id = Column(Integer, ForeignKey("knowledge_physical_files.file_id"), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=True) # 使用 bge-m3 1024维向量
    is_deleted = Column(Boolean, index=True, nullable=False, default=False)
    kb_tier = Column(SQLEnum(KBTier), nullable=False)
    security_level = Column(SQLEnum(DataSecurityLevel), nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=True)
    owner_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=True)
    metadata_json = Column(JSONB, nullable=False, default={})