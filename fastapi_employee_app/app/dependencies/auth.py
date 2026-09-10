"""
app/dependencies/auth.py

Authentication dependencies used to protect routes.

WHAT IS DEPENDENCY INJECTION (DI) IN FASTAPI?
------------------------------------------------
Dependency Injection means a route function declares what it NEEDS (a DB
session, the current logged-in user, ...) as parameters, and FastAPI is
responsible for building and supplying ("injecting") those values before the
route body runs. Routes just consume `Depends(some_function)` -- they never
need to know how to build a session or how to validate a token themselves.

WHY `Depends()` IS USED
-------------------------
`Depends()` wraps a callable (a plain function here, per project rules --
no class-based dependencies) and tells FastAPI: "call this to get the
value for this parameter". Depends() enables:
  - Code reuse: the same `get_current_user` function protects every route
    that needs authentication, instead of copy-pasting token logic
  - Testability: dependencies can be swapped/overridden easily in tests
  - Composability: dependencies can depend on OTHER dependencies (see below,
    get_current_user depends on get_db)

HOW DEPENDENCIES ARE EXECUTED BY FASTAPI
-------------------------------------------
For each incoming request, FastAPI:
  1. Looks at the route's declared parameters and resolves each `Depends(...)`
  2. Builds a dependency graph (get_current_user needs get_db, which itself
     is a dependency) and resolves it in the correct order, calling each
     dependency function
  3. Passes the return values into the route function as arguments
  4. If a dependency raises an HTTPException, the whole request stops there
     and that exception becomes the HTTP response -- the route body never runs.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# OAuth2PasswordBearer tells FastAPI (and the /docs Swagger UI) that clients
# must send a "Authorization: Bearer <token>" header, and where to point the
# Swagger "Authorize" button's token-request flow (tokenUrl).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that extracts and validates the JWT from the Authorization
    header, then loads the corresponding User from the database.

    This is itself a dependency that DEPENDS on two other dependencies:
    `oauth2_scheme` (pulls the raw token string out of the request headers)
    and `get_db` (supplies a database session). FastAPI resolves all of this
    automatically before calling this function.

    Raises 401 Unauthorized if the token is missing, invalid, expired, or
    does not correspond to a real user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    A second-layer dependency on top of get_current_user.

    In this simple schema there is no `is_active` column, so this function
    currently just passes the user through -- but it exists as the correct
    EXTENSION POINT: if you later add an `is_active` / `is_disabled` flag to
    the User model, this is the single place to enforce it, and every route
    already using `Depends(get_current_active_user)` gets the check for free.
    """
    return current_user
