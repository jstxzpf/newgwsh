from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.models.document import Document, DocumentSnapshot
from app.models.system import DocumentApprovalLog, NBSWorkflowAudit
from app.models.enums import DocumentStatus, WorkflowNodeId, NotificationType
from app.core.sip import generate_sip_hash
from app.core.exceptions import BusinessException
from app.core.locks import acquire_redis_lock, release_redis_lock
from app.services.notification_service import NotificationService
import uuid
import re
from datetime import datetime, timezone

class DocumentService:
    @staticmethod
    async def init_document(db: AsyncSession, title: str, doc_type_id: int, creator_id: int, dept_id: int | None) -> str:
        doc_id = str(uuid.uuid4())
        new_doc = Document(
            doc_id=doc_id,
            title=title,
            doc_type_id=doc_type_id,
            dept_id=dept_id,
            creator_id=creator_id,
            status=DocumentStatus.DRAFTING
        )
        db.add(new_doc)
        audit = NBSWorkflowAudit(
            doc_id=doc_id, workflow_node_id=WorkflowNodeId.DRAFTING,
            operator_id=creator_id
        )
        db.add(audit)
        return doc_id

    @staticmethod
    async def auto_save_draft(db: AsyncSession, doc: Document, title: str | None, content: str | None, draft_content: str | None):
        if doc.ai_polished_content:
            if content is not None:
                raise BusinessException(400, "DIFF 模式下禁止覆盖主正文")
            if draft_content is not None:
                doc.draft_suggestion = draft_content
        else:
            if draft_content is not None:
                raise BusinessException(400, "SINGLE 模式下无需提交建议草稿")
            if content is not None:
                doc.content = content
        if title is not None:
            doc.title = title

    @staticmethod
    async def submit_document(db: AsyncSession, doc: Document, user_id: int):
        if doc.status != DocumentStatus.DRAFTING:
            raise BusinessException(409, "当前状态不可提交")

        doc.status = DocumentStatus.SUBMITTED
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        log = DocumentApprovalLog(
            doc_id=doc.doc_id,
            submitter_id=user_id,
            decision_status="SUBMITTED",
            submitted_at=now
        )
        db.add(log)

        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id,
            workflow_node_id=WorkflowNodeId.SUBMITTED,
            operator_id=user_id
        )
        db.add(audit)
        await db.flush()

        # Notify department head (dept_head_id) or users with role_level >= 5 in the same dept
        from app.models.user import Department, SystemUser
        dept_result = await db.execute(
            select(Department).where(Department.dept_id == doc.dept_id)
        )
        dept = dept_result.scalars().first()
        reviewer_ids: set[int] = set()
        if dept and dept.dept_head_id:
            reviewer_ids.add(dept.dept_head_id)
        else:
            reviewers_result = await db.execute(
                select(SystemUser.user_id).where(
                    SystemUser.dept_id == doc.dept_id,
                    SystemUser.role_level >= 5,
                    SystemUser.is_active == True
                )
            )
            for row in reviewers_result.scalars().all():
                reviewer_ids.add(row)
        for rid in reviewer_ids:
            await NotificationService.create(
                db, user_id=rid, ntype=NotificationType.DOC_APPROVED,
                doc_id=doc.doc_id,
                content=f"公文「{doc.title}」已提交，等待审核",
                trigger_user_id=user_id
            )

        return log.log_id

    @staticmethod
    async def revise_document(db: AsyncSession, doc: Document, user_id: int, username: str) -> dict:
        if doc.status != DocumentStatus.REJECTED:
            raise BusinessException(409, "公文当前状态不允许回退修改")

        token = str(uuid.uuid4())
        success = await acquire_redis_lock(doc.doc_id, user_id, username, token, ttl=180)
        if not success:
            raise BusinessException(409, "锁已被抢占，无法回退")

        doc.status = DocumentStatus.DRAFTING
        doc.ai_polished_content = None
        doc.draft_suggestion = None

        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id,
            workflow_node_id=WorkflowNodeId.REVISION,
            operator_id=user_id
        )
        db.add(audit)

        return {
            "doc_id": doc.doc_id,
            "new_status": DocumentStatus.DRAFTING,
            "lock_acquired": True,
            "lock_token": token,
            "lock_expires_at": (datetime.now(timezone.utc).timestamp() + 180)
        }

    @staticmethod
    async def apply_polish(db: AsyncSession, doc: Document, final_content: str, user_id: int):
        snapshot = DocumentSnapshot(
            doc_id=doc.doc_id,
            content=doc.content,
            trigger_event="POLISH_APPLIED",
            creator_id=user_id
        )
        db.add(snapshot)

        doc.content = final_content
        doc.ai_polished_content = None
        doc.draft_suggestion = None

        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id,
            workflow_node_id=WorkflowNodeId.POLISH_APPLIED,
            operator_id=user_id
        )
        db.add(audit)

    # ========================================================================
    # 科长审核 (SUBMITTED → REVIEWED / REJECTED)
    # ========================================================================
    @staticmethod
    async def process_review(db: AsyncSession, doc: Document, action: str, reviewer_id: int, comments: str | None):
        if action == "REJECT":
            if doc.status not in (DocumentStatus.SUBMITTED, DocumentStatus.REVIEWED):
                raise BusinessException(409, "当前状态不可驳回")
        elif doc.status != DocumentStatus.SUBMITTED:
            raise BusinessException(409, "当前状态不可审核通过")

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if action == "APPROVE":
            doc.status = DocumentStatus.REVIEWED
            doc.reviewed_by = reviewer_id
            doc.reviewed_at = now
            log = DocumentApprovalLog(
                doc_id=doc.doc_id, submitter_id=doc.creator_id, reviewer_id=reviewer_id,
                decision_status="REVIEWED", reviewed_at=now
            )
            workflow_node = WorkflowNodeId.REVIEWED
            notify_content = f"公文「{doc.title}」科长审核通过，待局长签发"
        elif action == "REJECT":
            if not comments:
                raise BusinessException(400, "驳回必须提供理由")
            doc.status = DocumentStatus.REJECTED
            doc.reviewer_id = reviewer_id
            log = DocumentApprovalLog(
                doc_id=doc.doc_id, submitter_id=doc.creator_id, reviewer_id=reviewer_id,
                decision_status="REJECTED", rejection_reason=comments, reviewed_at=now
            )
            workflow_node = WorkflowNodeId.REJECTED
            prev_status = "科长审核" if doc.status == DocumentStatus.REVIEWED else "待审核"
            notify_content = f"公文「{doc.title}」被驳回，理由：{comments}"
        else:
            raise BusinessException(400, "无效的审批动作")

        db.add(log)
        await db.flush()

        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id, workflow_node_id=workflow_node,
            operator_id=reviewer_id, reference_id=log.log_id,
            action_details={"reason": comments} if comments else {}
        )
        db.add(audit)

        # Notify document creator
        await NotificationService.create(
            db, user_id=doc.creator_id,
            ntype=NotificationType.DOC_APPROVED if action == "APPROVE" else NotificationType.DOC_REJECTED,
            doc_id=doc.doc_id, content=notify_content,
            trigger_user_id=reviewer_id
        )

        return log.log_id

    # ========================================================================
    # 局长签发 (REVIEWED → APPROVED) — generates document_number
    # ========================================================================
    @staticmethod
    async def issue_document(db: AsyncSession, doc: Document, issuer_id: int):
        if doc.status != DocumentStatus.REVIEWED:
            raise BusinessException(409, "当前状态不可签发，需先通过科长审核")

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Generate document number
        doc.document_number = await DocumentService._generate_document_number(db)
        doc.status = DocumentStatus.APPROVED
        doc.issued_by = issuer_id
        doc.issued_at = now
        doc.reviewer_id = issuer_id

        # SIP hash with final content
        sip = generate_sip_hash(doc.content or "", issuer_id, now.isoformat())
        log = DocumentApprovalLog(
            doc_id=doc.doc_id, submitter_id=doc.creator_id, reviewer_id=issuer_id,
            decision_status="APPROVED", sip_hash=sip, reviewed_at=now
        )
        db.add(log)
        await db.flush()

        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id, workflow_node_id=WorkflowNodeId.ISSUED,
            operator_id=issuer_id, reference_id=log.log_id,
            action_details={"document_number": doc.document_number}
        )
        db.add(audit)

        # Notify creator and reviewer
        notify_msg = f"公文「{doc.title}」已签发，发文编号：{doc.document_number}"
        await NotificationService.create(
            db, user_id=doc.creator_id, ntype=NotificationType.DOC_APPROVED,
            doc_id=doc.doc_id, content=notify_msg, trigger_user_id=issuer_id
        )
        if doc.reviewed_by and doc.reviewed_by != doc.creator_id:
            await NotificationService.create(
                db, user_id=doc.reviewed_by, ntype=NotificationType.DOC_APPROVED,
                doc_id=doc.doc_id, content=notify_msg, trigger_user_id=issuer_id
            )

        return log.log_id

    # ========================================================================
    # 归档 (APPROVED → ARCHIVED)
    # ========================================================================
    @staticmethod
    async def archive_document(db: AsyncSession, doc: Document, user_id: int):
        if doc.status != DocumentStatus.APPROVED:
            raise BusinessException(409, "仅已签发的公文可归档")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        doc.status = DocumentStatus.ARCHIVED
        doc.archived_by = user_id
        doc.archived_at = now

        audit = NBSWorkflowAudit(
            doc_id=doc.doc_id, workflow_node_id=WorkflowNodeId.ARCHIVED,
            operator_id=user_id,
            action_details={"document_number": doc.document_number}
        )
        db.add(audit)

        await NotificationService.create(
            db, user_id=doc.creator_id, ntype=NotificationType.DOC_APPROVED,
            doc_id=doc.doc_id,
            content=f"公文「{doc.title}」已归档",
            trigger_user_id=user_id
        )

    # ========================================================================
    # 分发 (records dispatch metadata, does not change status)
    # ========================================================================
    @staticmethod
    async def dispatch_document(db: AsyncSession, doc: Document, user_id: int, dept_ids: list[int]):
        if doc.status not in (DocumentStatus.APPROVED, DocumentStatus.ARCHIVED):
            raise BusinessException(409, "仅已签发或已归档的公文可分发给科室")

        doc.dispatch_depts = {"dispatched_to": dept_ids, "dispatched_by": user_id,
                               "dispatched_at": datetime.now(timezone.utc).isoformat()}

    # ========================================================================
    # 发文编号生成
    # ========================================================================
    @staticmethod
    async def _generate_document_number(db: AsyncSession) -> str:
        year = datetime.now(timezone.utc).year
        pattern = f"泰调字〔{year}〕%号"

        result = await db.execute(
            select(func.max(Document.document_number))
            .where(Document.document_number.like(pattern))
        )
        max_num = result.scalar()

        if max_num:
            match = re.search(r"〔(\d+)〕(\d+)号", max_num)
            if match:
                seq = int(match.group(2)) + 1
            else:
                seq = 1
        else:
            seq = 1

        return f"泰调字〔{year}〕{seq}号"

    # ========================================================================
    # SIP 验证
    # ========================================================================
    @staticmethod
    async def verify_sip(db: AsyncSession, doc_id: str) -> dict:
        result = await db.execute(
            select(DocumentApprovalLog)
            .where(DocumentApprovalLog.doc_id == doc_id, DocumentApprovalLog.decision_status == "APPROVED")
            .order_by(DocumentApprovalLog.reviewed_at.desc())
        )
        log = result.scalars().first()
        if not log or not log.sip_hash:
            return {"match": False, "reason": "未找到有效的审批存证记录"}

        doc_result = await db.execute(select(Document).where(Document.doc_id == doc_id))
        doc = doc_result.scalars().first()
        if not doc:
            raise BusinessException(404, "公文不存在")

        current_hash = generate_sip_hash(
            doc.content or "",
            log.reviewer_id,
            log.reviewed_at.isoformat()
        )

        return {
            "match": current_hash == log.sip_hash,
            "stored_hash": log.sip_hash,
            "calculated_hash": current_hash,
            "reviewer_id": log.reviewer_id,
            "reviewed_at": log.reviewed_at
        }

    @staticmethod
    async def create_snapshot(db: AsyncSession, doc_id: str, content: str, user_id: int, event: str):
        snapshot = DocumentSnapshot(
            doc_id=doc_id,
            content=content,
            trigger_event=event,
            creator_id=user_id
        )
        db.add(snapshot)
        return snapshot.snapshot_id
