import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.district import District
from app.schemas.district import DistrictCreate, DistrictUpdate

SORTABLE_COLUMNS = {"name": District.name, "created_at": District.created_at}


async def list_districts(
    db: AsyncSession,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[list[District], int]:
    if sort_by not in SORTABLE_COLUMNS:
        raise ValidationAppError(f"sort_by must be one of {sorted(SORTABLE_COLUMNS)}")
    if sort_order not in {"asc", "desc"}:
        raise ValidationAppError("sort_order must be 'asc' or 'desc'")

    column = SORTABLE_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()

    stmt = select(District)
    count_stmt = select(func.count()).select_from(District)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(District.name.ilike(pattern))
        count_stmt = count_stmt.where(District.name.ilike(pattern))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_district(db: AsyncSession, district_id: uuid.UUID) -> District:
    district = await db.get(District, district_id)
    if district is None:
        raise NotFoundError(f"District {district_id} not found")
    return district


async def _check_duplicate_code(
    db: AsyncSession, code: str, *, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = select(District).where(District.code == code)
    if exclude_id is not None:
        stmt = stmt.where(District.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"District code '{code}' already exists")


async def create_district(db: AsyncSession, payload: DistrictCreate) -> District:
    await _check_duplicate_code(db, payload.code)
    district = District(**payload.model_dump())
    db.add(district)
    await db.commit()
    await db.refresh(district)
    return district


async def update_district(
    db: AsyncSession, district_id: uuid.UUID, payload: DistrictUpdate
) -> District:
    district = await get_district(db, district_id)
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != district.code:
        await _check_duplicate_code(db, data["code"], exclude_id=district_id)
    for field, value in data.items():
        setattr(district, field, value)
    await db.commit()
    await db.refresh(district)
    return district


async def delete_district(db: AsyncSession, district_id: uuid.UUID) -> None:
    district = await get_district(db, district_id)
    await db.delete(district)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Cannot delete district because other records reference it") from exc
