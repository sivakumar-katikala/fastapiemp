"""
app/main.py

Application entrypoint. Creates the FastAPI app instance, wires up
middleware, routers, static files, exception handlers, and the startup
event that creates database tables.

THE FULL REQUEST FLOW (ASGI)
--------------------------------
    Browser
       |
       v
    Uvicorn (ASGI server)          <- translates raw HTTP into the ASGI protocol
       |
       v
    ASGI application (this `app`)   <- FastAPI itself
       |
       v
    Middleware (RequestLoggingMiddleware, CORS, ...)
       |
       v
    Dependency Injection (get_db, get_current_user, ...)
       |
       v
    Router  (auth.py / employees.py / pages.py)
       |
       v
    Service (auth_service.py / employee_service.py)   <- business logic
       |
       v
    Database (SQLite, via SQLAlchemy AsyncSession)
       |
       v
    Response flows back up through Middleware -> Uvicorn -> Browser

WHY ASGI, NOT WSGI?
-----------------------
WSGI (Web Server Gateway Interface) is the older standard used by
synchronous frameworks like Flask/Django (classic). A WSGI app handles ONE
request per worker thread at a time, blocking on I/O (like a slow DB query).
ASGI (Asynchronous Server Gateway Interface) is its modern successor: it
allows a single worker to handle MANY requests concurrently by using
`async`/`await` and yielding control during I/O waits (DB calls, external
HTTP calls, etc.), instead of blocking the whole worker.

FastAPI is built on Starlette and is ASGI-native -- it should always be run
with an ASGI server such as Uvicorn (`uvicorn app.main:app`), NOT with a WSGI
server like plain Gunicorn-sync-workers or mod_wsgi. (Gunicorn CAN be used,
but only as a process manager fronting Uvicorn's ASGI worker class.)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging_config import setup_logging
from app.middleware.logging import RequestLoggingMiddleware

# Configure logging (console + rotating file handler under logs/app.log)
# BEFORE anything else in the app runs, so every subsequent log call --
# including ones fired during router/model imports -- is captured correctly.
setup_logging(debug=settings.DEBUG)
logger = logging.getLogger("employee_app")

# Import models so their table metadata is registered with `Base` before
# `create_all` runs below. (If a model module is never imported, SQLAlchemy
# doesn't know about its table.)
from app.models import employee as _employee_model  # noqa: F401,E402
from app.models import user as _user_model  # noqa: F401,E402
from app.routers import auth, employees, pages  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle handler (replaces the older @app.on_event API).

    On startup: creates all database tables that don't exist yet, based on
    the SQLAlchemy models' metadata. In a real production system you would
    typically use a migration tool (e.g. Alembic) instead of create_all, but
    this keeps the example runnable with zero extra setup steps.
    """
    logger.info("Application starting up -- creating database tables if needed...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(
        "Startup complete. Database ready at postgresql://%s:%s/%s.",
        settings.POSTGRES_HOST, settings.POSTGRES_PORT, settings.POSTGRES_DB,
    )
    yield
    logger.info("Application shutting down.")
    # (No explicit shutdown cleanup needed; the engine's connection pool is
    # garbage collected with the process. For long-running services you
    # could call `await engine.dispose()` here.)


app = FastAPI(
    title=settings.APP_NAME,
    description="A complete Employee Management System built with FastAPI, "
    "SQLAlchemy 2.x (async), SQLite, JWT authentication, and a "
    "Bootstrap 5 frontend.",
    version="1.0.0",
    lifespan=lifespan,
)

# --- Middleware ---
# Order matters: middleware added last runs FIRST on the way in.
app.add_middleware(RequestLoggingMiddleware)

# CORS (Cross-Origin Resource Sharing): allows this API to be called from a
# web page served on a DIFFERENT origin (different host/port/protocol) than
# this API itself -- e.g. a frontend dev server on http://localhost:5173
# calling this API on http://127.0.0.1:8000. Without this, a BROWSER (not
# Postman -- Postman doesn't enforce CORS) would first send an OPTIONS
# "preflight" request for any POST/PUT/PATCH/DELETE call with a JSON body or
# Authorization header, and -- with no route registered for OPTIONS -- that
# preflight would fail with 405 Method Not Allowed, which then blocks the
# real request from ever being sent. `allow_origins=["*"]` is intentionally
# permissive here since this is a local/learning project; restrict this to
# your actual frontend's origin(s) before deploying anywhere real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static files (CSS/JS) ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- Routers ---
app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(pages.router)


# --------------------------------------------------------------------------
# Centralized error handlers -- ensures consistent JSON error responses and
# proper status codes across the whole API, per the spec's error handling
# requirements (duplicate email, invalid body, DB errors, etc.).
# --------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Triggered automatically whenever a request body/query/path fails Pydantic
    validation (e.g. missing required field, bad email format, salary <= 0).
    Returns HTTP 422 Unprocessable Entity with a structured error list.
    """
    logger.warning(
        "Validation error on %s %s: %s", request.method, request.url.path, exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Catches unexpected database errors and returns a generic 500, instead
    of leaking raw database internals/stack traces to the client. The full
    exception (with traceback) is still written to the log file for
    debugging -- `logger.exception` automatically includes the traceback."""
    logger.exception(
        "Database error on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred. Please try again later."},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Ensures every HTTPException (401, 403, 404, 409, ...) raised anywhere in
    the app -- routers, dependencies, services -- is returned as a consistent
    `{"detail": "..."}` JSON body, and preserves any custom headers (like the
    `WWW-Authenticate` header set on 401 responses).
    """
    # 4xx responses are expected/client-caused -- log at INFO, not WARNING/ERROR,
    # to avoid flooding logs with routine 404s/401s. 5xx (rare for a plain
    # HTTPException, but possible if raised manually) logs louder.
    if exc.status_code >= 500:
        logger.error(
            "HTTPException %s on %s %s: %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    else:
        logger.info(
            "HTTPException %s on %s %s: %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None) or {},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all safety net for any exception NOT already handled by a more
    specific handler above (RequestValidationError, SQLAlchemyError,
    HTTPException). This should rarely fire in normal operation -- it exists
    so that a genuine bug (a typo, a None where an object was expected, a
    third-party library raising something unexpected, etc.) NEVER crashes
    the whole worker process or leaks a raw Python traceback to the client.

    The full traceback is still captured in the log file (`logger.exception`
    automatically attaches it) so you can debug it -- the client just gets a
    safe, generic 500 message.
    """
    logger.exception(
        "Unhandled exception on %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


@app.get("/health", tags=["Health"], summary="Simple health check endpoint")
async def health_check():
    """Used to verify the app + event loop are up. Doesn't touch the DB."""
    return {"status": "ok", "app": settings.APP_NAME}
