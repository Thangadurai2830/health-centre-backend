import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.system import router as system_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.error_handler import register_exception_handlers
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting %s in %s mode", settings.PROJECT_NAME, settings.ENVIRONMENT)
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.APP_VERSION,
        description="Production foundation for the SwasthyaSetu platform API.",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "system", "description": "Root, version, and probe endpoints."},
            {
                "name": "auth",
                "description": (
                    "Mobile OTP authentication: send/verify OTP, JWT access and refresh "
                    "tokens, profile, and session management."
                ),
            },
            {"name": "health", "description": "Infrastructure dependency health checks."},
            {"name": "health-centres", "description": "Health centre directory operations."},
            {"name": "districts", "description": "District master data management."},
            {"name": "blocks", "description": "Block master data management."},
            {"name": "villages", "description": "Village master data management."},
            {"name": "departments", "description": "Global department catalog management."},
            {
                "name": "wards",
                "description": "Ward management, tying departments to health centres.",
            },
            {"name": "rooms", "description": "Room management within wards."},
            {"name": "specializations", "description": "Specialization catalog management."},
            {
                "name": "staff",
                "description": "Staff assignment and transfer between health centres.",
            },
            {"name": "lookups", "description": "Lightweight flat lookup lists for dropdowns."},
        ],
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)
    app.include_router(system_router)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
