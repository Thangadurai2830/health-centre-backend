import logging

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.redis import get_redis
from app.db.session import get_db
from app.schemas.common import DependencyHealthResponse, HealthCheckResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=HealthCheckResponse,
    summary="Application health",
    description="Returns whether the application process is up and which environment it is running in.",
)
async def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="ok", environment=settings.ENVIRONMENT)


@router.get(
    "/database",
    response_model=DependencyHealthResponse,
    summary="Database health",
    description="Checks connectivity to PostgreSQL by executing a lightweight query.",
    responses={
        503: {"description": "Database is unreachable"},
    },
)
async def database_health(db: AsyncSession = Depends(get_db)) -> DependencyHealthResponse:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Database health check failed")
        return DependencyHealthResponse(status="error", detail=str(exc))
    return DependencyHealthResponse(status="ok")


@router.get(
    "/redis",
    response_model=DependencyHealthResponse,
    summary="Redis health",
    description="Checks connectivity to Redis by issuing a PING command.",
    responses={
        503: {"description": "Redis is unreachable"},
    },
)
async def redis_health(redis: Redis = Depends(get_redis)) -> DependencyHealthResponse:
    try:
        await redis.ping()
    except Exception as exc:
        logger.exception("Redis health check failed")
        return DependencyHealthResponse(status="error", detail=str(exc))
    return DependencyHealthResponse(status="ok")
