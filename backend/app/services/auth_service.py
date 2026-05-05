from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from app.models.user import UserSession
import uuid
from datetime import datetime, timedelta, timezone

class AuthService:
    @staticmethod
    async def clear_user_sessions(db: AsyncSession, user_id: int):
        await db.execute(delete(UserSession).where(UserSession.user_id == user_id))

    @staticmethod
    async def create_session(db: AsyncSession, user_id: int, refresh_token_hash: str) -> str:
        session_id = str(uuid.uuid4())
        # 使用 naive UTC datetime 适配 TIMESTAMP WITHOUT TIME ZONE
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        new_session = UserSession(
            session_id=session_id,
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=now + timedelta(days=7)
        )
        db.add(new_session)
        return session_id