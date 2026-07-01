import logging

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.redis import get_redis
from app.db.session import get_db
from app.schemas.common import LivenessResponse, ReadinessResponse, RootResponse, VersionResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get(
    "/",
    response_model=RootResponse,
    summary="API root",
    description="Root endpoint confirming the API is reachable.",
)
async def root() -> RootResponse:
    return RootResponse(
        name=settings.PROJECT_NAME,
        status="ok",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    )


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Application version",
    description="Returns the deployed application name, version, and environment.",
)
async def version() -> VersionResponse:
    return VersionResponse(
        name=settings.PROJECT_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Kubernetes-style liveness probe. Returns alive as long as the process is running.",
)
async def live() -> LivenessResponse:
    return LivenessResponse(status="alive")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Kubernetes-style readiness probe. Checks that the database and Redis "
        "are reachable before reporting ready."
    ),
    responses={
        503: {"description": "One or more dependencies are unavailable"},
    },
)
async def ready(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ReadinessResponse:
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception("Readiness check: database unavailable")
        checks["database"] = "error"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        logger.exception("Readiness check: redis unavailable")
        checks["redis"] = "error"

    overall = "ready" if all(v == "ok" for v in checks.values()) else "not_ready"
    return ReadinessResponse(status=overall, checks=checks)
