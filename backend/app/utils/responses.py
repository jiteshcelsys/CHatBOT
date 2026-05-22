"""
Thin wrappers so route handlers read like:
    return success({"key": "value"})
    return error("NOT_FOUND", "Item not found.", 404)
"""
from typing import Any

from fastapi.responses import JSONResponse

from app.schemas.base import ApiResponse


def success(data: Any = None, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ApiResponse.ok(data).model_dump(),
    )


def error(code: str, message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ApiResponse.fail(code, message).model_dump(),
    )
