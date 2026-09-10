"""
app/routers/pages.py

Routes that render server-side HTML pages (Jinja2 templates) for the
Bootstrap 5 frontend. These are separate from the JSON API routers
(auth.py, employees.py) -- they just return HTML shells; the actual data
(employee lists, login, etc.) is fetched client-side via JavaScript
(see static/js/app.js) calling the JSON API with the stored JWT.

NOTE ON TemplateResponse'S SIGNATURE
----------------------------------------
Current Starlette (>=0.37, which this project pins via FastAPI) expects:

    templates.TemplateResponse(request, "name.html", {...context...})

with `request` as the first positional argument -- NOT inside the context
dict as `{"request": request, ...}` (that was the older, now-removed style).
Starlette auto-injects `request` into the template context for you.
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", summary="Redirect root to the login page (HTML)")
async def root_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"active": "login"})


@router.get("/signup", summary="Signup page (HTML)")
async def signup_page(request: Request):
    return templates.TemplateResponse(request, "signup.html", {"active": "signup"})


@router.get("/login", summary="Login page (HTML)")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"active": "login"})


@router.get("/dashboard", summary="Employee dashboard (HTML)")
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"active": "dashboard"})


@router.get("/employees-page", summary="Employee records page (HTML)")
async def employees_page(request: Request):
    return templates.TemplateResponse(request, "employees.html", {"active": "employees"})


@router.get("/employees-page/new", summary="Add employee form page (HTML)")
async def employee_form_page(request: Request):
    return templates.TemplateResponse(
        request,
        "employee_form.html",
        {"active": "employees", "mode": "create", "employee_id": "null"},
    )


@router.get("/employees-page/{employee_id}/edit", summary="Edit employee form page (HTML)")
async def employee_edit_page(request: Request, employee_id: int):
    return templates.TemplateResponse(
        request,
        "employee_form.html",
        {"active": "employees", "mode": "edit", "employee_id": employee_id},
    )


@router.get("/employees-page/{employee_id}", summary="Employee details page (HTML)")
async def employee_detail_page(request: Request, employee_id: int):
    return templates.TemplateResponse(
        request,
        "employee_detail.html",
        {"active": "employees", "employee_id": employee_id},
    )
