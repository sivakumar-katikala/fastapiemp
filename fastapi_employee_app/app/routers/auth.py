"""
app/routers/auth.py

Authentication routes: signup and login.

These are PUBLIC endpoints (no Depends(get_current_user)) since a user
obviously can't be authenticated before they have an account or a token yet.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import Token
from app.schemas.user import UserResponse, UserSignup
from app.services.auth_service import (
    DuplicateUserError,
    InvalidCredentialsError,
    authenticate_user,
    issue_access_token_for_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(payload: UserSignup, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account.

    - Validates the request body with the `UserSignup` Pydantic schema
      (email format, password length/strength, matching confirm_password).
    - Hashes the password before storing it (see app/core/security.py).
    - Returns 409 Conflict if the username or email is already registered.
    """
    try:
        user = await register_user(db, payload)
    except DuplicateUserError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Log in and receive a JWT access token",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and issue a JWT access token.

    Uses FastAPI's standard `OAuth2PasswordRequestForm` dependency, which
    expects `username` and `password` as form fields (this is what powers
    the "Authorize" button in the /docs Swagger UI). Internally we treat
    `form_data.username` as either a username -- extend `authenticate_user`
    if you also want to allow logging in by email.

    Returns 401 Unauthorized for any invalid username/password combination.
    """
    try:
        user = await authenticate_user(db, form_data.username, form_data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    access_token = issue_access_token_for_user(user)
    return Token(access_token=access_token, token_type="bearer")
