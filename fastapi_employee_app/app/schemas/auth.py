"""
app/schemas/auth.py

Pydantic schemas related to JWT tokens.
"""

from pydantic import BaseModel


class Token(BaseModel):
    """Response body returned to the client after a successful login."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Internal representation of the data we expect to find decoded inside a
    JWT's payload. Used by the auth dependency to validate token contents.
    """

    username: str | None = None
