import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.specialization import Specialization
from app.schemas.specialization import SpecializationCreate, SpecializationUpdate

SORTABLE_COLUMNS = {"name": Specialization.name, "created_at": Specialization.created_at}


async def list_specializations(
    db: AsyncSession,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[list[Specialization], int]:
    if sort_by not in SORTABLE_COLUMNS:
        raise ValidationAppError(f"sort_by must be one of {sorted(SORTABLE_COLUMNS)}")
    if sort_order not in {"asc", "desc"}:
        raise ValidationAppError("sort_order must be 'asc' or 'desc'")

    column = SORTABLE_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()

    stmt = select(Specialization)
    count_stmt = select(func.count()).select_from(Specialization)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Specialization.name.ilike(pattern))
        count_stmt = count_stmt.where(Specialization.name.ilike(pattern))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_specialization(db: AsyncSession, specialization_id: uuid.UUID) -> Specialization:
    specialization = await db.get(Specialization, specialization_id)
    if specialization is None:
        raise NotFoundError(f"Specialization {specialization_id} not found")
    return specialization


async def _check_duplicate_name(
    db: AsyncSession, name: str, *, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = select(Specialization).where(Specialization.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Specialization.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Specialization '{name}' already exists")


async def create_specialization(db: AsyncSession, payload: SpecializationCreate) -> Specialization:
    await _check_duplicate_name(db, payload.name)
    specialization = Specialization(**payload.model_dump())
    db.add(specialization)
    await db.commit()
    await db.refresh(specialization)
    return specialization


async def update_specialization(
    db: AsyncSession, specialization_id: uuid.UUID, payload: SpecializationUpdate
) -> Specialization:
    specialization = await get_specialization(db, specialization_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != specialization.name:
        await _check_duplicate_name(db, data["name"], exclude_id=specialization_id)
    for field, value in data.items():
        setattr(specialization, field, value)
    await db.commit()
    await db.refresh(specialization)
    return specialization


async def delete_specialization(db: AsyncSession, specialization_id: uuid.UUID) -> None:
    specialization = await get_specialization(db, specialization_id)
    await db.delete(specialization)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            "Cannot delete specialization because other records reference it"
        ) from exc
