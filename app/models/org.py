from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.models.base import Base, TimestampMixin

class Department(Base, TimestampMixin):
    """科室组织表"""
    __tablename__ = "departments"

    dept_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dept_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="科室名称")
    dept_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="科室编码")
    dept_head_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True, comment="科室负责人ID")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")

    # 关系定义
    users: Mapped[List["SystemUser"]] = relationship("SystemUser", back_populates="department", foreign_keys="SystemUser.dept_id")

class SystemUser(Base, TimestampMixin):
    """系统用户表"""
    __tablename__ = "system_users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False, comment="工号/用户名")
    full_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="真实姓名")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希(Argon2id)")
    dept_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.dept_id"), index=True, nullable=False, comment="所属科室ID")
    role_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="角色等级: 99管理员, 5科长, 1科员")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")

    # 关系定义
    department: Mapped["Department"] = relationship("Department", back_populates="users", foreign_keys=[dept_id])
    sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="user")

class UserSession(Base, TimestampMixin):
    """用户会话表"""
    __tablename__ = "users_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="会话ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="Refresh Token哈希")
    access_jti: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="Access Token的JTI用于精准踢出")
    device_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="设备信息")
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), index=True, nullable=False, comment="过期时间")

    # 关系定义
    user: Mapped["SystemUser"] = relationship("SystemUser", back_populates="sessions")
