# FastAPI Employee Management System - Postman Testing Guide

## 1. Start the application

Open PowerShell in the project root:

```powershell
cd fastapi_employee_app
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Open Swagger:

`http://127.0.0.1:8000/docs`

## 2. Important: this project uses these employee URLs

- `POST /employees` - create employee
- `GET /employees` - list employees
- `GET /employees/{employee_id}` - get one employee
- `PUT /employees/{employee_id}` - update employee
- `PATCH /employees/{employee_id}` - partial update employee
- `DELETE /employees/{employee_id}` - delete employee

Do not use `/employees/register` with this version of the project. That URL belongs to a different version of the application.

## 3. Create a user

`POST http://127.0.0.1:8000/auth/signup`

Body -> raw -> JSON:

```json
{
  "username": "admin1",
  "email": "admin1@example.com",
  "password": "Admin12345",
  "confirm_password": "Admin12345"
}
```

## 4. Login

`POST http://127.0.0.1:8000/auth/login`

Body -> `x-www-form-urlencoded`:

| KEY | VALUE |
|---|---|
| username | admin1 |
| password | Admin12345 |

Do not send JSON for login.

Copy the returned `access_token`.

## 5. Create employee

`POST http://127.0.0.1:8000/employees`

Authorization -> Bearer Token -> paste the access token.

Body -> raw -> JSON:

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe.postman@example.com",
  "phone": "1234567890",
  "age": 30,
  "gender": "Male",
  "department": "Engineering",
  "designation": "Software Developer",
  "salary": 75000,
  "joining_date": "2024-01-15",
  "address": "123 Main Street",
  "city": "Hyderabad",
  "state": "Telangana",
  "country": "India"
}
```

The response is `201 Created`. Copy the returned `employee_id`.

## 6. PUT

`PUT http://127.0.0.1:8000/employees/<employee_id>`

Use the ID returned by POST.

Example body:

```json
{
  "salary": 90000,
  "designation": "Senior Software Developer"
}
```

This project's PUT endpoint accepts optional fields, so this partial body is valid.

## 7. PATCH

`PATCH http://127.0.0.1:8000/employees/<employee_id>`

Example body:

```json
{
  "department": "Product"
}
```

## 8. DELETE

`DELETE http://127.0.0.1:8000/employees/<employee_id>`

Expected success response: `204 No Content`.

## 9. Understanding 404

If the response is:

```json
{"detail":"Not Found"}
```

check the URL. For this project use `/employees`, not `/employees/register`.

If the response is:

```json
{"detail":"Employee with id 4 not found"}
```

then the route is correct, but that employee ID does not exist in the current database.

The `Time: 7 ms` shown by Postman is only the response time; it is not the cause of the 404.
