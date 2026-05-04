from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base

class Department(Base):
    __tablename__ = "departments"
    dept_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dept_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    dept_code: Mapped[str | None] = mapped_column(String(32), unique=True)
    dept_head_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    members = relationship("SystemUser", back_populates="department", foreign_keys="SystemUser.dept_id")
    head = relationship("SystemUser", foreign_keys=[dept_head_id], post_update=True)

class SystemUser(Base):
    __tablename__ = "system_users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    dept_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.dept_id"), index=True)
    role_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    department = relationship("Department", back_populates="members", foreign_keys=[dept_id])
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="creator")

class UserSession(Base):
    __tablename__ = "users_sessions"
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    access_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    created_at: Mapped[func.now] = mapped_column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    user = relationship("SystemUser", back_populates="sessions")

from datetime import datetime