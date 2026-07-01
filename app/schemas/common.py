from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    environment: str


class ErrorResponse(BaseModel):
    error_code: str
    message: str
