"""
app/middleware/logging.py

Custom ASGI middleware for request logging and timing.

WHAT IS MIDDLEWARE AND WHERE DOES IT RUN?
--------------------------------------------
Middleware wraps EVERY request/response cycle, running code both before the
request reaches your route (and its dependencies) and after the response is
generated, before it is sent back to the client:

    Client -> Uvicorn -> [Middleware: before] -> Dependencies -> Route
              -> Database -> Response -> [Middleware: after] -> Client

This makes middleware the right place for cross-cutting concerns that apply
to (almost) all requests: logging, timing, adding response headers, CORS,
etc. -- logic that doesn't belong in any single route.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# NOTE: actual handler/format setup (console + rotating file) now lives in
# app/core/logging_config.py, called once from main.py at startup. This
# module just grabs the named logger and uses it -- it does NOT call
# basicConfig() itself, to avoid configuring logging twice.
logger = logging.getLogger("employee_app")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs basic information about every request: method, path, status code,
    and how long it took to process. Also stamps each request with a unique
    ID (useful for tracing a single request through log files).

    If an unhandled exception escapes the route entirely (not caught by any
    of the exception handlers in main.py -- which shouldn't normally happen,
    but could for a genuine bug), this middleware still logs it with the
    full traceback and the request context, then re-raises so Starlette's
    own error handling can still produce a response.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        # --- "before" phase: runs before the route/dependencies execute ---
        logger.info(
            "[%s] --> %s %s", request_id, request.method, request.url.path
        )

        try:
            # `call_next` hands control to the rest of the ASGI pipeline
            # (remaining middleware, then dependency injection, then route).
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "[%s] !! UNHANDLED EXCEPTION on %s %s after %.2fms",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        # --- "after" phase: runs once the route has produced a response ---
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            log_level,
            "[%s] <-- %s %s status=%s duration=%.2fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        # Expose timing/tracing info to the client via response headers too.
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

        return response
