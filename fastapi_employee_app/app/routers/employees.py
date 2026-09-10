"""
app/routers/employees.py

Employee CRUD routes. ALL routes here require a valid JWT
(`Depends(get_current_active_user)`), demonstrating protected endpoints.

PATH vs QUERY vs BODY vs HEADER vs DEPENDENCY PARAMETERS
------------------------------------------------------------
- Path parameter:      `employee_id` in `/employees/{employee_id}` -- part of the URL path itself.
- Query parameter:     `?department=IT&page=1` -- key/value pairs after `?` in the URL.
- Request body:        the JSON payload for POST/PUT, parsed into a Pydantic model (EmployeeCreate/EmployeeUpdate).
- Header parameter:    e.g. the `Authorization: Bearer <token>` header, read by the oauth2_scheme dependency.
- Dependency parameter: `db` and `current_user` below -- values FastAPI computes by calling another function via Depends().

FastAPI tells these apart by how each parameter is declared/annotated,
not by name -- e.g. Pydantic-model-typed parameters are treated as body,
plain types default to query (for GET) unless part of the path, etc.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employee_service import (
    DuplicateEmployeeEmailError,
    EmployeeNotFoundError,
    create_employee,
    delete_employee,
    get_employee_by_id,
    list_employees,
    update_employee,
)

router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
    dependencies=[Depends(get_current_active_user)],  # applies auth to every route below
)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new employee",
)
async def create_employee_route(
    payload: EmployeeCreate,  # <-- REQUEST BODY parameter, validated by Pydantic
    db: AsyncSession = Depends(get_db),  # <-- DEPENDENCY parameter
    current_user: User = Depends(get_current_active_user),  # <-- DEPENDENCY parameter
):
    """Insert a new employee record. Requires authentication."""
    try:
        employee = await create_employee(db, payload, created_by=current_user.id)
    except DuplicateEmployeeEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return employee


@router.get(
    "",
    response_model=EmployeeListResponse,
    summary="List employees with optional filtering and pagination",
)
async def list_employees_route(
    db: AsyncSession = Depends(get_db),
    department: str | None = Query(default=None, description="Filter by department, e.g. IT"),
    city: str | None = Query(default=None, description="Filter by city, e.g. Hyderabad"),
    search: str | None = Query(default=None, description="Search by first/last name or email"),
    page: int = Query(default=1, ge=1, description="Page number, starting at 1"),
    limit: int = Query(default=10, ge=1, le=100, description="Results per page (max 100)"),
):
    """
    List employees.

    Examples:
    - `GET /employees?department=IT`
    - `GET /employees?department=IT&city=Hyderabad`
    - `GET /employees?page=1&limit=10`

    `department`, `city`, and `search` are QUERY PARAMETERS -- optional
    filters read from the URL's `?key=value` pairs. `page`/`limit` implement
    simple offset-based pagination.
    """
    employees, total = await list_employees(
        db, department=department, city=city, search=search, page=page, limit=limit
    )
    return EmployeeListResponse(total=total, page=page, limit=limit, items=employees)


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get a single employee by ID",
)
async def get_employee_route(
    employee_id: int,  # <-- PATH parameter
    db: AsyncSession = Depends(get_db),
):
    """Fetch full details for one employee. Returns 404 if not found."""
    try:
        employee = await get_employee_by_id(db, employee_id)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return employee


@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update an existing employee (full or partial)",
)
async def update_employee_route(
    employee_id: int,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an employee. Only fields provided in the body are changed."""
    try:
        employee = await update_employee(db, employee_id, payload)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateEmployeeEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return employee


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Partially update an existing employee",
)
async def patch_employee_route(
    employee_id: int,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    PATCH is the HTTP-standard verb for a PARTIAL update (only send the
    fields you want to change), while PUT is conventionally used for a FULL
    replacement of the resource. This project's `EmployeeUpdate` schema
    already makes every field optional, so both verbs behave identically
    here -- this route exists so clients that specifically expect PATCH
    (many frontend libraries and REST conventions default to it for partial
    updates) don't hit a 405 Method Not Allowed. It reuses the exact same
    `update_employee` service function as PUT above -- no logic is
    duplicated, just the route registration.
    """
    try:
        employee = await update_employee(db, employee_id, payload)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateEmployeeEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return employee


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an employee",
)
async def delete_employee_route(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an employee record. Returns 204 No Content on success."""
    try:
        await delete_employee(db, employee_id)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return None
