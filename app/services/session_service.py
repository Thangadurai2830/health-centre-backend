import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.session import Session, SessionStatus
from app.schemas.auth import DeviceInfo


async def create_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    device: DeviceInfo | None,
    ip_address: str | None,
) -> Session:
    now = datetime.now(UTC)
    session = Session(
        user_id=user_id,
        device_name=device.device_name if device else None,
        device_type=device.device_type if device else None,
        device_os=device.device_os if device else None,
        browser=device.browser if device else None,
        ip_address=ip_address,
        login_time=now,
        last_activity=now,
        status=SessionStatus.ACTIVE,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> Session:
    session = await db.get(Session, session_id)
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")
    return session


async def touch_session(db: AsyncSession, session: Session) -> None:
    session.last_activity = datetime.now(UTC)
    await db.commit()


async def list_active_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[Session]:
    stmt = (
        select(Session)
        .where(Session.user_id == user_id, Session.status == SessionStatus.ACTIVE)
        .order_by(Session.last_activity.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def end_session(db: AsyncSession, session: Session, *, status: SessionStatus) -> None:
    session.status = status
    session.logout_time = datetime.now(UTC)
    await db.commit()


async def revoke_session_for_user(
    db: AsyncSession, *, user_id: uuid.UUID, session_id: uuid.UUID
) -> Session:
    session = await get_session(db, session_id)
    if session.user_id != user_id:
        raise ForbiddenError("Cannot revoke a session that does not belong to this user")
    await end_session(db, session, status=SessionStatus.REVOKED)
    return session


async def end_all_sessions(db: AsyncSession, user_id: uuid.UUID) -> None:
    sessions = await list_active_sessions(db, user_id)
    for session in sessions:
        session.status = SessionStatus.LOGGED_OUT
        session.logout_time = datetime.now(UTC)
    await db.commit()
