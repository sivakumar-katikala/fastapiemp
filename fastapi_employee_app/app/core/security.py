"""
app/core/security.py

Password hashing and JWT (JSON Web Token) helper functions.

These are plain functions (no classes/inheritance) that routers and services
call directly. Keeping them here means authentication-related cryptography
logic lives in exactly one place in the codebase.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# CryptContext configures passlib to use bcrypt for hashing.
# bcrypt automatically salts each hash, so identical passwords produce
# different hashes -- this defends against rainbow-table attacks.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password for storage. Never store raw passwords."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT access token.

    `data` typically contains the "sub" (subject) claim -- here, the user's
    username or id -- identifying who the token belongs to. We add an "exp"
    (expiration) claim so the token automatically becomes invalid after a
    set time, limiting the damage if a token is ever leaked.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT.

    Returns the decoded payload dict if the token is valid and not expired,
    or None if the token is invalid, tampered with, or expired. The caller
    (an auth dependency) is responsible for turning `None` into an HTTP 401.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
