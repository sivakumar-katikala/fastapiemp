"""
app/services/auth_service.py

Business logic for signup and login, kept separate from:
  - app/routers/auth.py   (HTTP layer: request parsing, status codes)
  - app/models/user.py    (database representation)

Routers call these functions; these functions talk to the database and
apply business rules (e.g. "usernames must be unique").
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserSignup


class DuplicateUserError(Exception):
    """Raised when a signup attempt reuses an existing username or email."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials don't match any active user."""


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, payload: UserSignup) -> User:
    """
    Create a new user account.

    Steps:
      1. Check that the username and email are not already taken.
      2. Hash the plain-text password (never store it as-is).
      3. Insert the new user row and commit.
    """
    existing_username = await get_user_by_username(db, payload.username)
    if existing_username is not None:
        raise DuplicateUserError("Username is already taken")

    existing_email = await get_user_by_email(db, payload.email)
    if existing_email is not None:
        raise DuplicateUserError("Email is already registered")

    new_user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
    """
    Verify a username + password pair and return the matching user.

    Raises InvalidCredentialsError if the username doesn't exist or the
    password is wrong. We deliberately raise the SAME error in both cases
    (rather than a distinct "user not found" error) to avoid leaking which
    usernames are registered to an attacker probing the login endpoint.
    """
    user = await get_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Incorrect username or password")
    return user


def issue_access_token_for_user(user: User) -> str:
    """Build a signed JWT for a successfully authenticated user."""
    return create_access_token(data={"sub": user.username})
