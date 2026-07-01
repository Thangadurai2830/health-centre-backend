import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.health_centre import HealthCentreCreate, HealthCentreRead, HealthCentreUpdate
from app.services import health_centre_service

router = APIRouter()


@router.get("", response_model=list[HealthCentreRead])
async def list_centres(
    district_id: uuid.UUID | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
) -> list[HealthCentreRead]:
    centres = await health_centre_service.list_health_centres(
        db, district_id=district_id, limit=limit, offset=offset
    )
    return [HealthCentreRead.model_validate(c) for c in centres]


@router.get("/{centre_id}", response_model=HealthCentreRead)
async def get_centre(
    centre_id: uuid.UUID, db: AsyncSession = Depends(get_session)
) -> HealthCentreRead:
    centre = await health_centre_service.get_health_centre(db, centre_id)
    return HealthCentreRead.model_validate(centre)


@router.post("", response_model=HealthCentreRead, status_code=status.HTTP_201_CREATED)
async def create_centre(
    payload: HealthCentreCreate, db: AsyncSession = Depends(get_session)
) -> HealthCentreRead:
    centre = await health_centre_service.create_health_centre(db, payload)
    return HealthCentreRead.model_validate(centre)


@router.patch("/{centre_id}", response_model=HealthCentreRead)
async def update_centre(
    centre_id: uuid.UUID, payload: HealthCentreUpdate, db: AsyncSession = Depends(get_session)
) -> HealthCentreRead:
    centre = await health_centre_service.update_health_centre(db, centre_id, payload)
    return HealthCentreRead.model_validate(centre)


@router.delete("/{centre_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_centre(centre_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> None:
    await health_centre_service.delete_health_centre(db, centre_id)
