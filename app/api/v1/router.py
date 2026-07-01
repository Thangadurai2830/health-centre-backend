from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, health_centres

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(health_centres.router, prefix="/health-centres", tags=["health-centres"])
