from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.schemas.base import ApiResponse
from app.schemas.health import HealthData
from app.utils.responses import success

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthData])
async def health_check() -> JSONResponse:
    settings = get_settings()
    return success(
        HealthData(status="ok", env=settings.app_env, version="0.1.0").model_dump()
    )
