"""
app/core/config.py

Centralized application configuration.

WHY THIS FILE EXISTS
---------------------
Hardcoding secrets (DB passwords, JWT secret keys) directly in source code is a
security risk and makes the app impossible to configure differently across
environments (local/dev/staging/prod). Instead, we read configuration from
environment variables (via a ".env" file in development) using
`pydantic-settings`. This gives us:
  - Validation of config values at startup (fail fast if something is missing)
  - A single, typed source of truth (`settings`) that the rest of the app imports
  - Easy overriding via real environment variables in production (Docker, etc.)
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Typed application settings. Values are loaded from environment variables
    or from a ".env" file (see `model_config` below). Pydantic validates the
    types automatically -- e.g. ACCESS_TOKEN_EXPIRE_MINUTES must be an int.
    """

    # --- App metadata ---
    APP_NAME: str = "Employee Management System"
    DEBUG: bool = True

    # --- SQLite database settings ---
    # Just a filename -- SQLite stores the whole database in a single file
    # on disk, so there's no server, user, password, or port to configure.
    DB_NAME: str = "employee_management.db"

    # --- JWT / security settings ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def DATABASE_URL_ASYNC(self) -> str:
        """
        Async SQLAlchemy connection string, using the aiosqlite driver.
        Used by the app at runtime for non-blocking DB I/O.
        """
        return f"sqlite+aiosqlite:///./{self.DB_NAME}"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    `lru_cache` ensures the .env file / environment is only parsed once per
    process, and every part of the app that calls get_settings() shares the
    same Settings object instead of re-reading and re-validating every time.
    """
    return Settings()


# A ready-to-import singleton, used throughout the app: `from app.core.config import settings`
settings = get_settings()
