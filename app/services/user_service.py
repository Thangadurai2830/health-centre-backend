import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.user import UserProfileRead, UserProfileUpdate

PROFILE_FIELDS = ("full_name", "email", "language")


async def get_user_by_mobile(db: AsyncSession, mobile_number: str) -> User | None:
    stmt = select(User).where(User.mobile_number == mobile_number, User.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


async def get_or_create_user(
    db: AsyncSession, *, mobile_number: str, country_code: str
) -> tuple[User, bool]:
    user = await get_user_by_mobile(db, mobile_number)
    if user is not None:
        return user, False

    user = User(mobile_number=mobile_number, country_code=country_code, is_verified=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, True


async def mark_login(db: AsyncSession, user: User) -> None:
    user.last_login = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)


async def update_profile(db: AsyncSession, user: User, payload: UserProfileUpdate) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


def compute_profile_completion_percent(user: User) -> int:
    filled = sum(1 for field in PROFILE_FIELDS if getattr(user, field))
    return round((filled / len(PROFILE_FIELDS)) * 100)


def to_profile_read(user: User) -> UserProfileRead:
    return UserProfileRead(
        id=user.id,
        mobile_number=user.mobile_number,
        country_code=user.country_code,
        full_name=user.full_name,
        email=user.email,
        language=user.language,
        role=user.role,
        status=user.status,
        is_verified=user.is_verified,
        profile_completion_percent=compute_profile_completion_percent(user),
        created_at=user.created_at,
        last_login=user.last_login,
    )
