import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(
            "X-Correlation-ID", str(uuid.uuid4())
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration = (
                time.perf_counter() - start_time
            ) * 1000

            logger.exception(
                "Unhandled exception",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration, 2),
                },
            )
            raise

        duration = (time.perf_counter() - start_time) * 1000

        logger.info(
            "HTTP request",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
            },
        )

        response.headers["X-Correlation-ID"] = correlation_id
        return response
