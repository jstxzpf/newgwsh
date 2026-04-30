import enum
from typing import Optional
from sqlalchemy import String, Enum, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, validates
from app.models.base import Base, TimestampMixin

class DocStatus(enum.IntEnum):
    DRAFTING = 10    # 起草中
    SUBMITTED = 30   # 已提交（审批中）
    APPROVED = 40    # 已通过 (终态)
    REJECTED = 41    # 已驳回

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[DocStatus] = mapped_column(
        Enum(DocStatus), 
        default=DocStatus.DRAFTING,
        insert_default=DocStatus.DRAFTING,
        comment="公文状态"
    )

    def __init__(self, **kwargs):
        if "status" not in kwargs:
            kwargs["status"] = DocStatus.DRAFTING
        super().__init__(**kwargs)
    version: Mapped[int] = mapped_column(Integer, default=1, comment="版本号")
    creator_id: Mapped[int] = mapped_column(Integer, index=True, comment="创建人ID")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否软删除")

    @validates("status")
    def validate_status_transition(self, key, new_status):
        if not hasattr(self, "status") or self.status is None:
            return new_status

        old_status = self.status
        if old_status == new_status:
            return new_status

        # 核心状态机转换防线
        valid_transitions = {
            DocStatus.DRAFTING: [DocStatus.SUBMITTED],
            DocStatus.SUBMITTED: [DocStatus.APPROVED, DocStatus.REJECTED],
            DocStatus.REJECTED: [DocStatus.DRAFTING],
            DocStatus.APPROVED: [],  # 终态，不允许任何转换
        }

        if new_status not in valid_transitions.get(old_status, []):
            raise ValueError(
                f"Invalid status transition from {old_status.name} to {new_status.name}"
            )
        
        return new_status
