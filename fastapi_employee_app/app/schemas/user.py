"""
app/schemas/user.py

Pydantic v2 schemas for user signup, login, and API responses.

These are completely separate from the SQLAlchemy `User` model in
app/models/user.py. FastAPI uses these classes to:
  1. Parse and VALIDATE incoming JSON request bodies (UserSignup, UserLogin)
  2. Shape and SERIALIZE outgoing JSON responses (UserResponse), making sure
     sensitive fields like password_hash are never accidentally leaked.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserSignup(BaseModel):
    """Request body for POST /auth/signup."""

    username: str = Field(min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(description="A valid, unique email address")
    password: str = Field(min_length=8, max_length=128, description="Plain-text password (will be hashed)")
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        """
        Basic password strength rule: require at least one letter and one
        digit. Real production systems may enforce stricter rules (special
        characters, breach-list checks, etc.) -- this keeps the example simple.
        """
        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter")
        return value

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, value: str, info) -> str:
        """Ensures 'password' and 'confirm_password' are identical."""
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("Passwords do not match")
        return value


class UserLogin(BaseModel):
    """Request body for POST /auth/login."""

    username: str = Field(min_length=3, max_length=50, description="Username or email")
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """
    Public-facing representation of a user, returned by the API.
    Deliberately excludes password_hash.
    """

    id: int
    username: str
    email: EmailStr
    created_at: datetime

    # from_attributes=True lets this schema be built directly from a
    # SQLAlchemy ORM object (model.id, model.username, ...) instead of
    # requiring a plain dict.
    model_config = ConfigDict(from_attributes=True)
