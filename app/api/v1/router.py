from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    block,
    department,
    district,
    health,
    health_centres,
    lookups,
    room,
    specialization,
    staff_assignment,
    village,
    ward,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(health_centres.router, prefix="/health-centres", tags=["health-centres"])
api_router.include_router(district.router, prefix="/districts", tags=["districts"])
api_router.include_router(block.router, prefix="/blocks", tags=["blocks"])
api_router.include_router(village.router, prefix="/villages", tags=["villages"])
api_router.include_router(department.router, prefix="/departments", tags=["departments"])
api_router.include_router(ward.router, prefix="/wards", tags=["wards"])
api_router.include_router(room.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(
    specialization.router, prefix="/specializations", tags=["specializations"]
)
api_router.include_router(staff_assignment.router, prefix="/staff", tags=["staff"])
api_router.include_router(lookups.router, prefix="/lookups", tags=["lookups"])
