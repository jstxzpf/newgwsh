from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Department(Base):
    __tablename__ = "departments"
    
    dept_id = Column(Integer, primary_key=True, autoincrement=True)
    dept_name = Column(String(128), unique=True, nullable=False)
    dept_code = Column(String(32), unique=True)
    dept_head_id = Column(Integer, ForeignKey("system_users.user_id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="department", foreign_keys="[User.dept_id]")


class User(Base):
    __tablename__ = "system_users"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    dept_id = Column(Integer, ForeignKey("departments.dept_id"), index=True)
    role_level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    department = relationship("Department", back_populates="users", foreign_keys=[dept_id])


class UserSession(Base):
    __tablename__ = "users_sessions"
    
    session_id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("system_users.user_id"), index=True, nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    device_info = Column(String(255), nullable=True)
    expires_at = Column(DateTime, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
