"""
app/models/user.py

SQLAlchemy ORM model for the "users" table.

NOTE: SQLAlchemy models describe database structure ONLY (table/columns).
They are NOT used directly for API request/response validation -- that job
belongs to the Pydantic schemas in app/schemas/. This separation means the
database shape and the API's public contract can evolve independently.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Represents an application user who can log in and manage employees."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # One user can create many employee records (one-to-many relationship).
    # `back_populates` links this to Employee.created_by_user for two-way access.
    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="created_by_user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
