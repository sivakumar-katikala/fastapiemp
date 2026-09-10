"""
app/services/employee_service.py

Business logic for creating, reading, updating, and deleting employees.
Kept separate from the HTTP layer (app/routers/employees.py) so the same
logic could be reused elsewhere (e.g. a future CLI tool or background job)
without duplicating it.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


class DuplicateEmployeeEmailError(Exception):
    """Raised when creating/updating an employee with an email already in use."""


class EmployeeNotFoundError(Exception):
    """Raised when an employee_id does not correspond to any row."""


async def _email_taken(db: AsyncSession, email: str, exclude_id: int | None = None) -> bool:
    stmt = select(Employee).where(Employee.email == email)
    if exclude_id is not None:
        stmt = stmt.where(Employee.employee_id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_employee(
    db: AsyncSession, payload: EmployeeCreate, created_by: int | None
) -> Employee:
    """Insert a new employee row into the database."""
    if await _email_taken(db, payload.email):
        raise DuplicateEmployeeEmailError("An employee with this email already exists")

    employee = Employee(**payload.model_dump(), created_by=created_by)
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


async def get_employee_by_id(db: AsyncSession, employee_id: int) -> Employee:
    """Fetch a single employee by primary key, or raise EmployeeNotFoundError."""
    employee = await db.get(Employee, employee_id)
    if employee is None:
        raise EmployeeNotFoundError(f"Employee with id {employee_id} not found")
    return employee


async def list_employees(
    db: AsyncSession,
    *,
    department: str | None = None,
    city: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 10,
) -> tuple[list[Employee], int]:
    """
    Query employees with optional filters (department, city, free-text search
    across name/email) and pagination.

    Returns a tuple of (page_of_employees, total_matching_count) so the
    router/response can build a proper paginated response.
    """
    stmt = select(Employee)
    count_stmt = select(func.count()).select_from(Employee)

    if department:
        stmt = stmt.where(Employee.department.ilike(f"%{department}%"))
        count_stmt = count_stmt.where(Employee.department.ilike(f"%{department}%"))

    if city:
        stmt = stmt.where(Employee.city.ilike(f"%{city}%"))
        count_stmt = count_stmt.where(Employee.city.ilike(f"%{city}%"))

    if search:
        pattern = f"%{search}%"
        search_filter = (
            Employee.first_name.ilike(pattern)
            | Employee.last_name.ilike(pattern)
            | Employee.email.ilike(pattern)
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * limit
    stmt = stmt.order_by(Employee.employee_id).offset(offset).limit(limit)

    result = await db.execute(stmt)
    employees = list(result.scalars().all())

    return employees, total


async def update_employee(db: AsyncSession, employee_id: int, payload: EmployeeUpdate) -> Employee:
    """Apply a partial update to an existing employee."""
    employee = await get_employee_by_id(db, employee_id)

    update_data = payload.model_dump(exclude_unset=True)

    if "email" in update_data and await _email_taken(db, update_data["email"], exclude_id=employee_id):
        raise DuplicateEmployeeEmailError("An employee with this email already exists")

    for field, value in update_data.items():
        setattr(employee, field, value)

    await db.commit()
    await db.refresh(employee)
    return employee


async def delete_employee(db: AsyncSession, employee_id: int) -> None:
    """Delete an employee record."""
    employee = await get_employee_by_id(db, employee_id)
    await db.delete(employee)
    await db.commit()
