from sqlalchemy import String, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.models.base import Base, TimestampMixin

class DocumentType(Base, TimestampMixin):
    """公文文种配置表"""
    __tablename__ = "document_types"

    type_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, comment="文种编码(如NOTICE)")
    type_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="文种名称(如通知)")
    layout_rules: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}', nullable=False, comment="排版要素规则JSON")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")

class SystemConfig(Base, TimestampMixin):
    """系统全局配置持久化表"""
    __tablename__ = "system_config"

    config_key: Mapped[str] = mapped_column(String(64), primary_key=True, comment="配置键")
    config_value: Mapped[str] = mapped_column(String(255), nullable=False, comment="配置值")
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="配置说明")
    value_type: Mapped[str] = mapped_column(String(16), default="string", nullable=False, comment="值类型: int/float/bool/string")
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("system_users.user_id"), nullable=True, comment="最后修改人ID")

    # 关系定义
    updater: Mapped[Optional["SystemUser"]] = relationship("SystemUser", foreign_keys=[updated_by])
