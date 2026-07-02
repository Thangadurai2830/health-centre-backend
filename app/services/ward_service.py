import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.department import Department
from app.models.health_centre import HealthCentre
from app.models.ward import Ward
from app.schemas.ward import WardCreate, WardUpdate

SORTABLE_COLUMNS = {"name": Ward.name, "created_at": Ward.created_at}


async def list_wards(
    db: AsyncSession,
    *,
    health_centre_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[list[Ward], int]:
    if sort_by not in SORTABLE_COLUMNS:
        raise ValidationAppError(f"sort_by must be one of {sorted(SORTABLE_COLUMNS)}")
    if sort_order not in {"asc", "desc"}:
        raise ValidationAppError("sort_order must be 'asc' or 'desc'")

    column = SORTABLE_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()

    stmt = select(Ward)
    count_stmt = select(func.count()).select_from(Ward)
    if health_centre_id is not None:
        stmt = stmt.where(Ward.health_centre_id == health_centre_id)
        count_stmt = count_stmt.where(Ward.health_centre_id == health_centre_id)
    if department_id is not None:
        stmt = stmt.where(Ward.department_id == department_id)
        count_stmt = count_stmt.where(Ward.department_id == department_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Ward.name.ilike(pattern))
        count_stmt = count_stmt.where(Ward.name.ilike(pattern))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_ward(db: AsyncSession, ward_id: uuid.UUID) -> Ward:
    ward = await db.get(Ward, ward_id)
    if ward is None:
        raise NotFoundError(f"Ward {ward_id} not found")
    return ward


async def _ensure_health_centre_exists(db: AsyncSession, health_centre_id: uuid.UUID) -> None:
    centre = await db.get(HealthCentre, health_centre_id)
    if centre is None:
        raise NotFoundError(f"Health centre {health_centre_id} not found")


async def _ensure_department_exists(db: AsyncSession, department_id: uuid.UUID) -> None:
    department = await db.get(Department, department_id)
    if department is None:
        raise NotFoundError(f"Department {department_id} not found")


async def _check_duplicate_name(
    db: AsyncSession,
    health_centre_id: uuid.UUID,
    name: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> None:
    stmt = select(Ward).where(Ward.health_centre_id == health_centre_id, Ward.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Ward.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Ward '{name}' already exists in this health centre")


async def create_ward(db: AsyncSession, payload: WardCreate) -> Ward:
    await _ensure_health_centre_exists(db, payload.health_centre_id)
    await _ensure_department_exists(db, payload.department_id)
    await _check_duplicate_name(db, payload.health_centre_id, payload.name)
    ward = Ward(**payload.model_dump())
    db.add(ward)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(f"Ward '{payload.name}' already exists in this health centre") from exc
    await db.refresh(ward)
    return ward


async def update_ward(db: AsyncSession, ward_id: uuid.UUID, payload: WardUpdate) -> Ward:
    ward = await get_ward(db, ward_id)
    data = payload.model_dump(exclude_unset=True)
    if "department_id" in data and data["department_id"] is not None:
        await _ensure_department_exists(db, data["department_id"])
    if "name" in data and data["name"] != ward.name:
        await _check_duplicate_name(db, ward.health_centre_id, data["name"], exclude_id=ward_id)
    for field, value in data.items():
        setattr(ward, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            f"Ward '{data.get('name', ward.name)}' already exists in this health centre"
        ) from exc
    await db.refresh(ward)
    return ward


async def delete_ward(db: AsyncSession, ward_id: uuid.UUID) -> None:
    ward = await get_ward(db, ward_id)
    await db.delete(ward)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Cannot delete ward because other records reference it") from exc
