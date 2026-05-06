from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system import UserNotification
from app.models.enums import NotificationType
from app.core.locks import redis_client
import json


class NotificationService:
    # Maps NotificationType to SSE event type string that frontend expects
    _EVENT_MAP = {
        NotificationType.DOC_APPROVED: "notification.approved",
        NotificationType.DOC_REJECTED: "notification.rejected",
        NotificationType.LOCK_RECLAIMED: "notification.lock_reclaimed",
        NotificationType.TASK_COMPLETED: "task.completed",
        NotificationType.TASK_FAILED: "task.failed",
    }

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        ntype: NotificationType,
        doc_id: str | None = None,
        content: str | None = None,
        trigger_user_id: int | None = None,
    ) -> UserNotification:
        notif = UserNotification(
            user_id=user_id,
            trigger_user_id=trigger_user_id,
            doc_id=doc_id,
            type=ntype,
            content=content,
        )
        db.add(notif)
        await db.flush()

        # Push real-time event to SSE channel so frontend bell badge updates live
        event_type = NotificationService._EVENT_MAP.get(ntype, "notification.unknown")
        payload = {
            "type": event_type,
            "notification_id": notif.notification_id,
            "doc_id": doc_id,
            "content": content,
        }
        # Include rejection_reason when present (frontend displays it)
        if ntype == NotificationType.DOC_REJECTED:
            payload["rejection_reason"] = content
        await redis_client.publish(f"user_events:{user_id}", json.dumps(payload, ensure_ascii=False))

        return notif
