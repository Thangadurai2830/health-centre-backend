import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.room import Room
from app.models.ward import Ward
from app.schemas.room import RoomCreate, RoomUpdate

SORTABLE_COLUMNS = {"room_number": Room.room_number, "created_at": Room.created_at}


async def list_rooms(
    db: AsyncSession,
    *,
    ward_id: uuid.UUID | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "room_number",
    sort_order: str = "asc",
) -> tuple[list[Room], int]:
    if sort_by not in SORTABLE_COLUMNS:
        raise ValidationAppError(f"sort_by must be one of {sorted(SORTABLE_COLUMNS)}")
    if sort_order not in {"asc", "desc"}:
        raise ValidationAppError("sort_order must be 'asc' or 'desc'")

    column = SORTABLE_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()

    stmt = select(Room)
    count_stmt = select(func.count()).select_from(Room)
    if ward_id is not None:
        stmt = stmt.where(Room.ward_id == ward_id)
        count_stmt = count_stmt.where(Room.ward_id == ward_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Room.room_number.ilike(pattern))
        count_stmt = count_stmt.where(Room.room_number.ilike(pattern))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_room(db: AsyncSession, room_id: uuid.UUID) -> Room:
    room = await db.get(Room, room_id)
    if room is None:
        raise NotFoundError(f"Room {room_id} not found")
    return room


async def _ensure_ward_exists(db: AsyncSession, ward_id: uuid.UUID) -> None:
    ward = await db.get(Ward, ward_id)
    if ward is None:
        raise NotFoundError(f"Ward {ward_id} not found")


async def _check_duplicate_room_number(
    db: AsyncSession,
    ward_id: uuid.UUID,
    room_number: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> None:
    stmt = select(Room).where(Room.ward_id == ward_id, Room.room_number == room_number)
    if exclude_id is not None:
        stmt = stmt.where(Room.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Room number '{room_number}' already exists in this ward")


async def create_room(db: AsyncSession, payload: RoomCreate) -> Room:
    await _ensure_ward_exists(db, payload.ward_id)
    await _check_duplicate_room_number(db, payload.ward_id, payload.room_number)
    room = Room(**payload.model_dump())
    db.add(room)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            f"Room number '{payload.room_number}' already exists in this ward"
        ) from exc
    await db.refresh(room)
    return room


async def update_room(db: AsyncSession, room_id: uuid.UUID, payload: RoomUpdate) -> Room:
    room = await get_room(db, room_id)
    data = payload.model_dump(exclude_unset=True)
    if "room_number" in data and data["room_number"] != room.room_number:
        await _check_duplicate_room_number(
            db, room.ward_id, data["room_number"], exclude_id=room_id
        )
    for field, value in data.items():
        setattr(room, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            f"Room number '{data.get('room_number', room.room_number)}' already exists "
            "in this ward"
        ) from exc
    await db.refresh(room)
    return room


async def delete_room(db: AsyncSession, room_id: uuid.UUID) -> None:
    room = await get_room(db, room_id)
    await db.delete(room)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Cannot delete room because other records reference it") from exc
