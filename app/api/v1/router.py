from fastapi import APIRouter

from app.api.v1.endpoints import health, health_centres

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(health_centres.router, prefix="/health-centres", tags=["health-centres"])
