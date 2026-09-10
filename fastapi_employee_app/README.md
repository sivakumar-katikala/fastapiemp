# Employee Management System — FastAPI

A complete, working Employee Management web application built with FastAPI,
async SQLAlchemy 2.x, SQLite, JWT authentication, and a Bootstrap 5
frontend.

## Tech Stack

- Python 3.11+
- FastAPI (ASGI) + Uvicorn
- SQLAlchemy 2.x (async, via `aiosqlite`)
- SQLite (single local database file, no server to install/run)
- Pydantic v2 / pydantic-settings
- Jinja2 templates + Bootstrap 5 + vanilla JS
- `python-jose` (JWT) + `passlib`/`bcrypt` (password hashing)

## Project Structure

```
fastapi_employee_app/
├── app/
│   ├── main.py                 # FastAPI app, middleware, routers, error handlers
│   ├── core/
│   │   ├── config.py           # Settings (env vars via pydantic-settings)
│   │   ├── security.py         # Password hashing + JWT create/decode
│   │   └── database.py         # Async engine/session, get_db() dependency
│   ├── models/                 # SQLAlchemy ORM models (User, Employee)
│   ├── schemas/                # Pydantic request/response schemas
│   ├── dependencies/
│   │   └── auth.py             # get_current_user / get_current_active_user
│   ├── middleware/
│   │   └── logging.py          # Request logging + timing middleware
│   ├── routers/                # auth.py, employees.py, pages.py (APIRouter)
│   ├── services/                # Business logic, separate from routes/DB models
│   ├── templates/              # Jinja2 HTML pages (Bootstrap 5)
│   └── static/                 # CSS/JS
├── .env.example                 # Copy to .env and fill in real values
├── requirements.txt
└── run.py                       # `python run.py` == `uvicorn app.main:app --reload`
```

## 1. Setup (Windows PowerShell)

```powershell
# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

> **Note on bcrypt version:** `requirements.txt` pins `bcrypt==3.2.2`
> alongside `passlib==1.7.4`. Newer `bcrypt` (4.1+) removed an internal
> attribute that `passlib` 1.7.4 probes at import time, which breaks
> password hashing. If you ever bump `passlib` to a newer release that
> fixes this, you can also bump `bcrypt`.

### Database setup

No database server to install — SQLite stores everything in a single local
file that's created automatically the first time the app runs.

A working `.env` file with a random `SECRET_KEY` already generated is
included in this project, so **you don't need to create or edit anything**
— you can skip straight to "Run the application" below.

If you'd rather generate your own `SECRET_KEY` (recommended if you plan to
share this project or deploy it anywhere), copy `.env.example` to `.env`
and set your own value:
```powershell
copy .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```
Paste the printed string into `.env` as `SECRET_KEY=...`.

Tables are created automatically on application startup (see the `lifespan`
handler in `app/main.py`) — no manual migration step is required for this
example project. The database file (e.g. `employee_management.db`) will
appear in the project's root folder once you run the app.

### Run the application

```powershell
uvicorn app.main:app --reload
```

or equivalently:

```powershell
python run.py
```

- App: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:8000/login
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

## 2. Using the App (Frontend)

1. Go to `/signup`, create an account.
2. Log in at `/login` — the JWT is stored in `sessionStorage` and attached
   automatically to API calls by `app/static/js/app.js`.
3. You'll land on `/dashboard`, showing a quick summary and recent employees.
4. Go to `/employees-page` to search/filter/paginate all employees, or
   `/employees-page/new` to add one.
5. Each row has **View / Edit / Delete** actions.

## 3. API Reference & Examples

All `/employees` routes require `Authorization: Bearer <token>`.

### Signup
```
POST /auth/signup
Content-Type: application/json

{
    "username": "sivak",
    "email": "sivak@example.com",
    "password": "Passw0rd123",
    "confirm_password": "Passw0rd123"
}
```
`201 Created`
```json
{
    "id": 1,
    "username": "sivak",
    "email": "sivak@example.com",
    "created_at": "2026-08-19T01:00:00"
}
```

### Login
```
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=sivak&password=Passw0rd123
```
`200 OK`
```json
{
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
}
```
> Note: `/auth/login` uses OAuth2's standard form-encoded body (not JSON) —
> this is what powers the "Authorize" button in Swagger UI (`/docs`).

### Create Employee
```
POST /employees
Authorization: Bearer <token>
Content-Type: application/json

{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "9876543210",
    "age": 28,
    "gender": "Male",
    "department": "IT",
    "designation": "Software Engineer",
    "salary": 50000,
    "joining_date": "2026-08-18",
    "address": "Main Road",
    "city": "Hyderabad",
    "state": "Telangana",
    "country": "India"
}
```
`201 Created` → returns the created `EmployeeResponse`.

### Get Employees (with filters + pagination)
```
GET /employees?department=IT&city=Hyderabad&page=1&limit=10
Authorization: Bearer <token>
```
`200 OK`
```json
{
    "total": 1,
    "page": 1,
    "limit": 10,
    "items": [ { "employee_id": 1, "first_name": "John", ... } ]
}
```

### Get Single Employee
```
GET /employees/1
Authorization: Bearer <token>
```

### Update Employee
```
PUT /employees/1
Authorization: Bearer <token>
Content-Type: application/json

{ "salary": 60000, "designation": "Senior Software Engineer" }
```
Partial update — only fields you include are changed.

### Delete Employee
```
DELETE /employees/1
Authorization: Bearer <token>
```
`204 No Content`

## 4. Error Handling

| Situation                     | Status |
|--------------------------------|--------|
| Validation error (bad body)    | 422    |
| Duplicate email / username     | 409    |
| Invalid login credentials      | 401    |
| Missing / invalid / expired JWT| 401    |
| Employee not found             | 404    |
| Wrong HTTP method for the URL  | 405    |
| Unexpected database error      | 500    |
| Any other unhandled exception  | 500    |

All error responses are JSON: `{"detail": "..."}` (422 also includes an
`errors` array with per-field messages).

### 405 Method Not Allowed — the exact method each URL supports

A `405` means the URL exists but you sent it a method it doesn't support —
it's the server correctly telling you "wrong verb," not a broken endpoint.
Here is the complete, exact list — every other method on these paths will
correctly 405:

| URL | Allowed methods |
|---|---|
| `/auth/signup` | `POST` only |
| `/auth/login` | `POST` only |
| `/employees` | `GET`, `POST` |
| `/employees/{employee_id}` | `GET`, `PUT`, `PATCH`, `DELETE` |
| `/health` | `GET` only |

Common mistakes that cause a 405:
- Sending `POST` to `/employees/{id}` (that URL has no create — POST only
  works on the plain `/employees` collection URL)
- Sending `PATCH` or `PUT` to `/employees` (partial/full updates only work
  on `/employees/{id}`, since you must target one specific record)
- Sending `GET`/`PUT`/`PATCH`/`DELETE` to `/auth/login` or `/auth/signup`
  (those are `POST`-only)
- A trailing slash mismatch, e.g. `/employees/` instead of `/employees`

If you hit a 405 anywhere else not listed above, that's a real bug — please
double check you're running the latest code in this package (this version
adds the `PATCH /employees/{id}` route, which earlier versions didn't have).

Four global exception handlers live in `app/main.py`, so every error in the
app — no matter which router, service, or dependency it comes from — is
guaranteed to return one of these consistent shapes instead of a raw stack
trace:

- `RequestValidationError` → 422, with the full list of per-field problems
- `HTTPException` → whatever status code was raised (401/404/409/...),
  preserving custom headers like `WWW-Authenticate`
- `SQLAlchemyError` → 500, hides raw database internals from the client
- `Exception` (catch-all) → 500, a final safety net so a genuine bug never
  crashes the server process or leaks a Python traceback to the client

Every one of these handlers also **logs** the error (see below) — the
client gets a safe, generic message, but the full detail (including a
traceback for 500s) is always written to `logs/app.log` for debugging.

## 5. Logging

Logging is centralized in `app/core/logging_config.py` and configured once,
at startup, from `app/main.py`. Every log line goes to **two** places at
once:

- **Console** — what you see live in your terminal while the app runs
- **`logs/app.log`** — a rotating log file on disk (capped at 5 MB, keeps
  the last 3 backups, then discards older ones — so it never grows
  unbounded)

```
2026-08-24 02:07:33 | INFO     | employee_app | [26a8d4ea] --> POST /employees
2026-08-24 02:07:33 | INFO     | employee_app | [26a8d4ea] <-- POST /employees status=201 duration=16.33ms
2026-08-24 02:07:33 | WARNING  | employee_app | [366661b2] <-- POST /employees status=409 duration=3.73ms
```

Every request gets a short unique ID (`[26a8d4ea]`) so you can grep the log
file for every line belonging to one specific request. Successful/expected
responses (2xx/3xx) log at `INFO`; client errors (4xx) log at `WARNING`;
server errors (5xx) and unhandled exceptions log at `ERROR`/`EXCEPTION`
(with a full traceback). Setting `DEBUG=True` in `.env` additionally
echoes the raw SQL SQLAlchemy generates for every query — useful while
developing, noisy in production, so it's off by default in spirit even
though this example ships with `DEBUG=True` for learning purposes.

## 6. Asynchronous Design

Every I/O-bound operation in this app — every database query, every route
handler — is `async`/`await`, running on FastAPI's ASGI event loop rather
than blocking a worker thread:

- **Routes** are all `async def` (`app/routers/*.py`)
- **Services** are all `async def` (`app/services/*.py`)
- **Database access** uses SQLAlchemy's `AsyncSession` and
  `create_async_engine`, driven by the `aiosqlite` async driver
  (`app/core/database.py`)
- **`get_db()`** is an async generator dependency — it `yield`s a session
  to the route and guarantees `session.close()` runs afterward even if the
  route raised an exception

This means a single Uvicorn worker can serve many concurrent requests
without one slow database query blocking every other in-flight request —
while one request is `await`ing the database, the event loop is free to
make progress on others.

## 7. Testing with Swagger UI (built into FastAPI)

FastAPI auto-generates interactive API docs from your code — no extra setup
needed. With the app running:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc (alternate docs view):** http://127.0.0.1:8000/redoc
- **Raw OpenAPI schema:** http://127.0.0.1:8000/openapi.json

To test protected endpoints in Swagger UI:
1. Expand `POST /auth/signup` → "Try it out" → fill in the body → Execute
   (creates a user)
2. Expand `POST /auth/login` → "Try it out" → fill in `username`/`password`
   → Execute → copy the `access_token` from the response
3. Click the green **Authorize** button near the top of the page → paste
   the token (just the token, Swagger adds the `Bearer ` prefix for you) →
   Authorize → Close
4. Every `/employees...` endpoint now automatically sends your token — just
   expand any of them, "Try it out", and Execute

## 8. Testing with the Postman Collection

A ready-to-import Postman collection and environment are included in the
`postman/` folder:

- `postman/Employee_Management.postman_collection.json` — every endpoint,
  organized into **Health**, **Auth**, **Employees**, and **Error Handling
  Examples** folders, each request with built-in test assertions
- `postman/Employee_Management.postman_environment.json` — `base_url`,
  `access_token`, `employee_id`, `username`, `password` variables

**Import steps:**
1. Open Postman → **Import** → select both JSON files from the `postman/`
   folder
2. In the top-right environment dropdown, select **"Employee Management -
   Local"**
3. Make sure the app is running (`python run.py`)
4. Run requests top-to-bottom, or click **Run collection** to execute all
   of them automatically via the Collection Runner

**The token handoff is automatic:** the `Login` request has a test script
that reads the `access_token` from its own response and saves it into the
environment. Every request under `Employees` reads
`Authorization: Bearer {{access_token}}` — you never copy/paste anything.
Likewise, `Create Employee` saves the new record's `employee_id`, which
`Get/Update/Delete Employee` then reuse automatically.

**Command-line run (via `newman`, Postman's CLI runner):**
```bash
npm install -g newman
newman run postman/Employee_Management.postman_collection.json \
  -e postman/Employee_Management.postman_environment.json
```
This runs the entire collection headlessly and prints a pass/fail report
for every request's assertions — useful for CI pipelines. This exact
command was used to verify this collection: **13 requests, 20 assertions,
0 failures** against a live instance of this app.

## 5. Architecture & Request Flow

```
Browser
   ↓
Uvicorn (ASGI server)
   ↓
FastAPI app (app/main.py)
   ↓
Middleware  (RequestLoggingMiddleware — logs + times every request)
   ↓
Dependency Injection  (Depends(get_db), Depends(get_current_active_user))
   ↓
Router  (app/routers/auth.py, employees.py, pages.py)
   ↓
Service  (app/services/auth_service.py, employee_service.py — business logic)
   ↓
SQLAlchemy (async ORM)
   ↓
SQLite
   ↓
Response flows back up through the same layers to the Browser
```

### Where each concept lives

- **ASGI / Uvicorn** — `run.py` and the `uvicorn app.main:app` command launch
  Uvicorn, an ASGI server. ASGI (unlike the older, synchronous WSGI standard)
  supports `async`/`await`, so a single worker can handle many concurrent
  requests without blocking on slow I/O (like a database call). FastAPI is
  ASGI-native and should never be deployed as if it were a WSGI app.
- **Middleware** — `app/middleware/logging.py`, registered in `app/main.py`
  via `app.add_middleware(...)`. Runs before and after every single request.
- **Dependency Injection / `Depends()`** — `app/core/database.py`
  (`get_db`) and `app/dependencies/auth.py` (`get_current_user`,
  `get_current_active_user`). Routes declare what they need as parameters;
  FastAPI builds and injects those values automatically. No class
  inheritance is used anywhere for this — just plain functions.
- **Pydantic** — `app/schemas/*.py`. Validates every request body
  (`UserSignup`, `EmployeeCreate`, ...) and shapes every response
  (`UserResponse`, `EmployeeResponse`, ...), completely separate from the
  SQLAlchemy models.
- **Query parameters** — `app/routers/employees.py`,
  `list_employees_route` (`department`, `city`, `search`, `page`, `limit`).
- **Request body** — `POST /employees`, `PUT /employees/{id}`, parsed via
  `EmployeeCreate` / `EmployeeUpdate`.
- **JWT** — `app/core/security.py` (`create_access_token`,
  `decode_access_token`), issued on login, validated on every protected
  request by `get_current_user`.
- **SQLAlchemy** — `app/models/*.py` (table definitions),
  `app/core/database.py` (async engine/session).
- **SQLite** — the actual database, connected to via `aiosqlite`. A single local file, no server process required.
- **API routers** — `app/routers/*.py`, each an `APIRouter` included into
  the main `app` in `app/main.py`.
- **Services** — `app/services/*.py`, the business-logic layer between
  routers and the database (uniqueness checks, password hashing calls,
  filtering/pagination logic).

### The full signup → protected request flow, step by step

1. `POST /auth/signup` → Pydantic validates the body (`UserSignup`) →
   `auth_service.register_user` hashes the password with bcrypt and inserts
   a new row into `users`.
2. `POST /auth/login` → `auth_service.authenticate_user` verifies the
   password hash → `create_access_token` signs a JWT containing
   `{"sub": username, "exp": ...}` → returned to the client.
3. Client stores the JWT and sends it as `Authorization: Bearer <token>` on
   every subsequent request.
4. `GET/POST/PUT/DELETE /employees...` → the `get_current_active_user`
   dependency (which itself depends on `get_current_user`) decodes and
   validates the JWT, loads the `User` row, and injects it into the route.
   If the token is missing/invalid/expired, a 401 is raised immediately and
   the route body never executes.
5. The route calls into `employee_service.py`, which builds and executes
   SQLAlchemy queries against SQLite via the async session, and returns
   ORM objects that Pydantic (`response_model=...`) serializes to JSON.
