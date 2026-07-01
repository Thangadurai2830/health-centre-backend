import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.health_centre import HealthCentre
from app.schemas.health_centre import HealthCentreCreate, HealthCentreUpdate


async def list_health_centres(
    db: AsyncSession, *, district_id: uuid.UUID | None = None, limit: int = 50, offset: int = 0
) -> list[HealthCentre]:
    stmt = select(HealthCentre).limit(limit).offset(offset)
    if district_id is not None:
        stmt = stmt.where(HealthCentre.district_id == district_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_health_centre(db: AsyncSession, centre_id: uuid.UUID) -> HealthCentre:
    centre = await db.get(HealthCentre, centre_id)
    if centre is None:
        raise NotFoundError(f"Health centre {centre_id} not found")
    return centre


async def create_health_centre(db: AsyncSession, payload: HealthCentreCreate) -> HealthCentre:
    centre = HealthCentre(**payload.model_dump())
    db.add(centre)
    await db.commit()
    await db.refresh(centre)
    return centre


async def update_health_centre(
    db: AsyncSession, centre_id: uuid.UUID, payload: HealthCentreUpdate
) -> HealthCentre:
    centre = await get_health_centre(db, centre_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(centre, field, value)
    await db.commit()
    await db.refresh(centre)
    return centre


async def delete_health_centre(db: AsyncSession, centre_id: uuid.UUID) -> None:
    centre = await get_health_centre(db, centre_id)
    await db.delete(centre)
    await db.commit()
