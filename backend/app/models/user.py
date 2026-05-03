from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Department(Base):
    __tablename__ = "departments"
    dept_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_name = Column(String(128), unique=True, nullable=False)
    dept_code = Column(String(32), unique=True)
    dept_head_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class SystemUser(Base):
    __tablename__ = "system_users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    full_name = Column(String(64), nullable=False)
    password_hash = Column(String(255), nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True)
    role_level = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class UserSession(Base):
    __tablename__ = "users_sessions"
    session_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    access_jti = Column(String(64), nullable=True)
    device_info = Column(String(255), nullable=True)
    expires_at = Column(DateTime, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())