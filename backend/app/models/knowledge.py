from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.enums import KBTier, DataSecurityLevel

class KnowledgePhysicalFile(Base):
    __tablename__ = "knowledge_physical_files"
    
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class KnowledgeBaseHierarchy(Base):
    __tablename__ = "knowledge_base_hierarchy"
    
    kb_id = Column(Integer, primary_key=True, autoincrement=True)
    parent_id = Column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), index=True, nullable=True)
    kb_name = Column(String(255), nullable=False)
    kb_type = Column(String(64), nullable=False) # FILE or DIRECTORY
    kb_tier = Column(Enum(KBTier), nullable=False, default=KBTier.PERSONAL)
    security_level = Column(Enum(DataSecurityLevel), nullable=False, default=DataSecurityLevel.GENERAL)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=True) # 追加：科室隔离
    parse_status = Column(String(64), nullable=False, default="READY")
    physical_file_id = Column(Integer, ForeignKey("knowledge_physical_files.file_id"), index=True, nullable=True)
    owner_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    file_version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    
    chunk_id = Column(Integer, primary_key=True, autoincrement=True)
    kb_id = Column(Integer, ForeignKey("knowledge_base_hierarchy.kb_id"), index=True, nullable=False)
    physical_file_id = Column(Integer, ForeignKey("knowledge_physical_files.file_id"), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True) # pgvector
    is_deleted = Column(Boolean, index=True, nullable=False, default=False)
    kb_tier = Column(Enum(KBTier), nullable=False)
    security_level = Column(Enum(DataSecurityLevel), nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=True)
    metadata_json = Column(JSONB, nullable=False, default={})
