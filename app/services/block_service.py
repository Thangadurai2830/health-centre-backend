import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.block import Block
from app.models.district import District
from app.schemas.block import BlockCreate, BlockUpdate

SORTABLE_COLUMNS = {"name": Block.name, "created_at": Block.created_at}


async def list_blocks(
    db: AsyncSession,
    *,
    district_id: uuid.UUID | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[list[Block], int]:
    if sort_by not in SORTABLE_COLUMNS:
        raise ValidationAppError(f"sort_by must be one of {sorted(SORTABLE_COLUMNS)}")
    if sort_order not in {"asc", "desc"}:
        raise ValidationAppError("sort_order must be 'asc' or 'desc'")

    column = SORTABLE_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()

    stmt = select(Block)
    count_stmt = select(func.count()).select_from(Block)
    if district_id is not None:
        stmt = stmt.where(Block.district_id == district_id)
        count_stmt = count_stmt.where(Block.district_id == district_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Block.name.ilike(pattern))
        count_stmt = count_stmt.where(Block.name.ilike(pattern))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_block(db: AsyncSession, block_id: uuid.UUID) -> Block:
    block = await db.get(Block, block_id)
    if block is None:
        raise NotFoundError(f"Block {block_id} not found")
    return block


async def _ensure_district_exists(db: AsyncSession, district_id: uuid.UUID) -> None:
    district = await db.get(District, district_id)
    if district is None:
        raise NotFoundError(f"District {district_id} not found")


async def _check_duplicate_code(
    db: AsyncSession,
    district_id: uuid.UUID,
    code: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> None:
    stmt = select(Block).where(Block.district_id == district_id, Block.code == code)
    if exclude_id is not None:
        stmt = stmt.where(Block.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Block code '{code}' already exists in this district")


async def create_block(db: AsyncSession, payload: BlockCreate) -> Block:
    await _ensure_district_exists(db, payload.district_id)
    await _check_duplicate_code(db, payload.district_id, payload.code)
    block = Block(**payload.model_dump())
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block


async def update_block(db: AsyncSession, block_id: uuid.UUID, payload: BlockUpdate) -> Block:
    block = await get_block(db, block_id)
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != block.code:
        await _check_duplicate_code(db, block.district_id, data["code"], exclude_id=block_id)
    for field, value in data.items():
        setattr(block, field, value)
    await db.commit()
    await db.refresh(block)
    return block


async def delete_block(db: AsyncSession, block_id: uuid.UUID) -> None:
    block = await get_block(db, block_id)
    await db.delete(block)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Cannot delete block because other records reference it") from exc
