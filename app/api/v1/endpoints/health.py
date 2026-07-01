from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import HealthCheckResponse

router = APIRouter()


@router.get("", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="ok", environment=settings.ENVIRONMENT)
