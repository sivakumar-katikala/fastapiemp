"""
app/core/database.py

Database engine and session configuration using ASYNCHRONOUS SQLAlchemy 2.x,
connected to a PostgreSQL server via the `asyncpg` driver.

SYNC vs ASYNC SQLAlchemy
-------------------------
- Sync SQLAlchemy (`Session`, `create_engine`) executes each database call in
  a blocking manner: the Python thread pauses until the database responds.
  This is simple but does not play well with FastAPI's async event loop -- a
  slow query would block the whole worker from handling other requests.
- Async SQLAlchemy (`AsyncSession`, `create_async_engine`) issues the same SQL
  but uses `await` under the hood, driven by an async DB driver (`asyncpg`
  here, talking to a real PostgreSQL server over the network/socket instead
  of reading a local file). While waiting on I/O, the event loop is free to
  handle other requests concurrently. This matches FastAPI's ASGI,
  non-blocking design.

We use ONLY the async pattern here (AsyncEngine + AsyncSession) throughout
the app, and never mix it with sync `Session` calls in request handlers --
mixing sync and async DB code in the same app is a common source of subtle
bugs and blocked event loops. (The standalone `seed_data.py` script is the
one exception -- it runs outside a request, so it uses the async pattern too
for consistency, sharing this same engine/session setup.)
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# The async engine manages a pool of database connections. `echo=settings.DEBUG`
# makes SQLAlchemy print the raw SQL it executes -- useful while learning/debugging,
# turn it off (DEBUG=False) in production to reduce log noise.
print("DATABASE URL:", settings.DATABASE_URL_ASYNC)
engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,  # Verifies connections are alive before using them
)

# async_sessionmaker builds new AsyncSession objects bound to our engine.
# expire_on_commit=False keeps ORM objects usable (e.g. for response
# serialization) after a commit, instead of forcing a re-fetch from the DB.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    Base class that all SQLAlchemy ORM models inherit from.
    SQLAlchemy uses this to collect model metadata (table names, columns)
    so it can create tables and build queries.
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session for a single request.

    HOW THIS DEPENDENCY WORKS
    ---------------------------
    FastAPI calls this generator function whenever a route declares
    `db: AsyncSession = Depends(get_db)`. Execution pauses at `yield session`,
    handing the session to the route function. Once the route finishes (or
    raises), execution resumes after the `yield`, closing the session in the
    `finally` block. This guarantees the connection is always released back
    to the pool, even if the request handler raises an exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
