import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import DBAPIError
from redis.exceptions import ConnectionError

from api.schemas.responses import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches all unhandled exceptions and returns them in a standard ErrorResponse envelope.
    """
    if isinstance(exc, HTTPException):
        # Convert standard FastAPI HTTPException to our envelope
        err = ErrorDetail(
            code="HTTP_ERROR",
            message=str(exc.detail),
            status=exc.status_code,
        )
        return JSONResponse(status_code=exc.status_code, content=ErrorResponse(error=err).model_dump())

    if isinstance(exc, DBAPIError):
        # Database connectivity or execution issues
        logger.error(f"Database error on {request.url.path}: {exc}")
        err = ErrorDetail(
            code="DATABASE_ERROR",
            message="A database error occurred. The service might be temporarily degraded.",
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        return JSONResponse(status_code=503, content=ErrorResponse(error=err).model_dump())

    if isinstance(exc, ConnectionError): # Redis
        logger.error(f"Redis connection error on {request.url.path}: {exc}")
        err = ErrorDetail(
            code="CACHE_ERROR",
            message="A caching service error occurred. The service might be temporarily degraded.",
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        return JSONResponse(status_code=503, content=ErrorResponse(error=err).model_dump())

    # Unhandled server errors fallback
    logger.error(f"Unhandled exception on {request.url.path}: {traceback.format_exc()}")
    err = ErrorDetail(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=500, content=ErrorResponse(error=err).model_dump())
