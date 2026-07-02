import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.geo import haversine_km
from app.models.block import Block
from app.models.district import District
from app.models.health_centre import CentreStatus, CentreType, HealthCentre
from app.models.village import Village
from app.schemas.health_centre import HealthCentreCreate, HealthCentreUpdate

SORTABLE_COLUMNS = {"name": HealthCentre.name, "created_at": HealthCentre.created_at}


async def list_health_centres(
    db: AsyncSession,
    *,
    district_id: uuid.UUID | None = None,
    block_id: uuid.UUID | None = None,
    village_id: uuid.UUID | None = None,
    type: CentreType | None = None,
    status: CentreStatus | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[list[HealthCentre], int]:
    if sort_by not in SORTABLE_COLUMNS:
        raise ValidationAppError(f"sort_by must be one of {sorted(SORTABLE_COLUMNS)}")
    if sort_order not in {"asc", "desc"}:
        raise ValidationAppError("sort_order must be 'asc' or 'desc'")

    column = SORTABLE_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()

    stmt = select(HealthCentre)
    count_stmt = select(func.count()).select_from(HealthCentre)

    filters = []
    if district_id is not None:
        filters.append(HealthCentre.district_id == district_id)
    if block_id is not None:
        filters.append(HealthCentre.block_id == block_id)
    if village_id is not None:
        filters.append(HealthCentre.village_id == village_id)
    if type is not None:
        filters.append(HealthCentre.type == type)
    if status is not None:
        filters.append(HealthCentre.status == status)
    if search:
        filters.append(HealthCentre.name.ilike(f"%{search}%"))

    for condition in filters:
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_health_centre(db: AsyncSession, centre_id: uuid.UUID) -> HealthCentre:
    centre = await db.get(HealthCentre, centre_id)
    if centre is None:
        raise NotFoundError(f"Health centre {centre_id} not found")
    return centre


async def _ensure_district_exists(db: AsyncSession, district_id: uuid.UUID) -> None:
    district = await db.get(District, district_id)
    if district is None:
        raise NotFoundError(f"District {district_id} not found")


async def _ensure_block_exists(db: AsyncSession, block_id: uuid.UUID) -> None:
    block = await db.get(Block, block_id)
    if block is None:
        raise NotFoundError(f"Block {block_id} not found")


async def _ensure_village_exists(db: AsyncSession, village_id: uuid.UUID) -> None:
    village = await db.get(Village, village_id)
    if village is None:
        raise NotFoundError(f"Village {village_id} not found")


async def _check_duplicate_name(
    db: AsyncSession,
    district_id: uuid.UUID,
    name: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> None:
    stmt = select(HealthCentre).where(
        HealthCentre.district_id == district_id, HealthCentre.name == name
    )
    if exclude_id is not None:
        stmt = stmt.where(HealthCentre.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Health centre '{name}' already exists in this district")


async def create_health_centre(db: AsyncSession, payload: HealthCentreCreate) -> HealthCentre:
    await _ensure_district_exists(db, payload.district_id)
    if payload.block_id is not None:
        await _ensure_block_exists(db, payload.block_id)
    if payload.village_id is not None:
        await _ensure_village_exists(db, payload.village_id)
    await _check_duplicate_name(db, payload.district_id, payload.name)

    centre = HealthCentre(**payload.model_dump())
    db.add(centre)
    await db.commit()
    await db.refresh(centre)
    return centre


async def update_health_centre(
    db: AsyncSession, centre_id: uuid.UUID, payload: HealthCentreUpdate
) -> HealthCentre:
    centre = await get_health_centre(db, centre_id)
    data = payload.model_dump(exclude_unset=True)

    if "block_id" in data and data["block_id"] is not None:
        await _ensure_block_exists(db, data["block_id"])
    if "village_id" in data and data["village_id"] is not None:
        await _ensure_village_exists(db, data["village_id"])
    if "name" in data and data["name"] != centre.name:
        await _check_duplicate_name(db, centre.district_id, data["name"], exclude_id=centre_id)

    for field, value in data.items():
        setattr(centre, field, value)
    await db.commit()
    await db.refresh(centre)
    return centre


async def delete_health_centre(db: AsyncSession, centre_id: uuid.UUID) -> None:
    centre = await get_health_centre(db, centre_id)
    await db.delete(centre)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(
            "Cannot delete health centre because other records reference it"
        ) from exc


async def list_nearby(
    db: AsyncSession,
    *,
    lat: float,
    lng: float,
    radius_km: float = 10,
    limit: int = 20,
) -> list[tuple[HealthCentre, float]]:
    stmt = select(HealthCentre).where(
        HealthCentre.status == CentreStatus.ACTIVE,
        HealthCentre.latitude.is_not(None),
        HealthCentre.longitude.is_not(None),
    )
    result = await db.execute(stmt)
    centres = result.scalars().all()

    nearby: list[tuple[HealthCentre, float]] = []
    for centre in centres:
        assert centre.latitude is not None
        assert centre.longitude is not None
        distance = haversine_km(lat, lng, centre.latitude, centre.longitude)
        if distance <= radius_km:
            nearby.append((centre, distance))

    nearby.sort(key=lambda pair: pair[1])
    return nearby[:limit]
