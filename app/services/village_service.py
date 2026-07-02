import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.block import Block
from app.models.village import Village
from app.schemas.village import VillageCreate, VillageUpdate

SORTABLE_COLUMNS = {"name": Village.name, "created_at": Village.created_at}


async def list_villages(
    db: AsyncSession,
    *,
    block_id: uuid.UUID | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[list[Village], int]:
    if sort_by not in SORTABLE_COLUMNS:
        raise ValidationAppError(f"sort_by must be one of {sorted(SORTABLE_COLUMNS)}")
    if sort_order not in {"asc", "desc"}:
        raise ValidationAppError("sort_order must be 'asc' or 'desc'")

    column = SORTABLE_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()

    stmt = select(Village)
    count_stmt = select(func.count()).select_from(Village)
    if block_id is not None:
        stmt = stmt.where(Village.block_id == block_id)
        count_stmt = count_stmt.where(Village.block_id == block_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Village.name.ilike(pattern))
        count_stmt = count_stmt.where(Village.name.ilike(pattern))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_village(db: AsyncSession, village_id: uuid.UUID) -> Village:
    village = await db.get(Village, village_id)
    if village is None:
        raise NotFoundError(f"Village {village_id} not found")
    return village


async def _ensure_block_exists(db: AsyncSession, block_id: uuid.UUID) -> None:
    block = await db.get(Block, block_id)
    if block is None:
        raise NotFoundError(f"Block {block_id} not found")


async def create_village(db: AsyncSession, payload: VillageCreate) -> Village:
    await _ensure_block_exists(db, payload.block_id)
    village = Village(**payload.model_dump())
    db.add(village)
    await db.commit()
    await db.refresh(village)
    return village


async def update_village(
    db: AsyncSession, village_id: uuid.UUID, payload: VillageUpdate
) -> Village:
    village = await get_village(db, village_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(village, field, value)
    await db.commit()
    await db.refresh(village)
    return village


async def delete_village(db: AsyncSession, village_id: uuid.UUID) -> None:
    village = await get_village(db, village_id)
    await db.delete(village)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Cannot delete village because other records reference it") from exc
