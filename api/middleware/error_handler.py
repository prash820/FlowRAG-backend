"""
Error handling middleware.

API Layer is responsible for this module.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from datetime import datetime

from api.schemas import ErrorResponse

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")

    error_response = ErrorResponse(
        error="HTTPException",
        message=str(exc.detail),
        timestamp=datetime.utcnow().isoformat(),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle validation exceptions."""
    logger.warning(f"Validation error: {exc.errors()}")

    error_response = ErrorResponse(
        error="ValidationError",
        message="Invalid request data",
        detail=str(exc.errors()),
        timestamp=datetime.utcnow().isoformat(),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        detail=str(exc) if logger.level <= logging.DEBUG else None,
        timestamp=datetime.utcnow().isoformat(),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )
