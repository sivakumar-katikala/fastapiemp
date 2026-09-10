"""
seed_data.py

Standalone script that connects DIRECTLY to your PostgreSQL server and:
  1. Creates all tables (users, employees) if they don't already exist,
     using the same SQLAlchemy models as the main app.
  2. Inserts one sample admin user + several sample employee rows, so you
     have real data to look at immediately -- in pgAdmin, `psql`, or through
     the API/UI -- without manually calling the signup/create-employee
     endpoints first.

This does NOT start the FastAPI server. It just talks to the database.
Run it once after creating the Postgres database and before (or after)
starting the app with `python run.py`.

USAGE
-----
    python seed_data.py

It is SAFE TO RUN MORE THAN ONCE: it checks for existing rows (by username
/ email) before inserting, so re-running it won't create duplicates or
crash on a unique-constraint violation.
"""

import asyncio
from datetime import date

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import hash_password
from app.models.employee import Employee
from app.models.user import User

# --- Sample data -----------------------------------------------------------

SAMPLE_USER = {
    "username": "admin",
    "email": "admin@example.com",
    "password": "Admin@123",  # plain text here, hashed before insert
}

SAMPLE_EMPLOYEES = [
    dict(
        first_name="Ravi", last_name="Kumar", email="ravi.kumar@example.com",
        phone="+919876543210", age=29, gender="Male",
        department="Engineering", designation="Software Engineer",
        salary=65000.00, joining_date=date(2023, 6, 12),
        address="12 MG Road", city="Hyderabad", state="Telangana", country="India",
    ),
    dict(
        first_name="Sneha", last_name="Reddy", email="sneha.reddy@example.com",
        phone="+919876543211", age=31, gender="Female",
        department="Human Resources", designation="HR Manager",
        salary=72000.00, joining_date=date(2022, 3, 4),
        address="45 Jubilee Hills", city="Hyderabad", state="Telangana", country="India",
    ),
    dict(
        first_name="Arjun", last_name="Mehta", email="arjun.mehta@example.com",
        phone="+919876543212", age=27, gender="Male",
        department="Sales", designation="Sales Executive",
        salary=48000.00, joining_date=date(2024, 1, 20),
        address="8 Baner Road", city="Pune", state="Maharashtra", country="India",
    ),
    dict(
        first_name="Priya", last_name="Sharma", email="priya.sharma@example.com",
        phone="+919876543213", age=35, gender="Female",
        department="Finance", designation="Finance Analyst",
        salary=80000.00, joining_date=date(2021, 9, 15),
        address="21 Park Street", city="Kolkata", state="West Bengal", country="India",
    ),
    dict(
        first_name="Karthik", last_name="Iyer", email="karthik.iyer@example.com",
        phone="+919876543214", age=24, gender="Male",
        department="Engineering", designation="QA Engineer",
        salary=52000.00, joining_date=date(2024, 7, 1),
        address="3 Anna Salai", city="Chennai", state="Tamil Nadu", country="India",
    ),
]


async def seed() -> None:
    # 1. Make sure the tables exist (same metadata the FastAPI app uses).
    print("Connecting to PostgreSQL and ensuring tables exist ...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables are ready.")

    async with AsyncSessionLocal() as db:
        # 2. Insert the sample admin user, if not already present.
        result = await db.execute(select(User).where(User.username == SAMPLE_USER["username"]))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                username=SAMPLE_USER["username"],
                email=SAMPLE_USER["email"],
                password_hash=hash_password(SAMPLE_USER["password"]),
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(
                f"Created user '{user.username}' "
                f"(login with username='{SAMPLE_USER['username']}', "
                f"password='{SAMPLE_USER['password']}')"
            )
        else:
            print(f"User '{user.username}' already exists -- skipping.")

        # 3. Insert sample employees, if not already present (by email).
        inserted = 0
        for emp_data in SAMPLE_EMPLOYEES:
            result = await db.execute(
                select(Employee).where(Employee.email == emp_data["email"])
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                continue
            employee = Employee(**emp_data, created_by=user.id)
            db.add(employee)
            inserted += 1

        await db.commit()
        print(f"Inserted {inserted} new employee row(s) "
              f"({len(SAMPLE_EMPLOYEES) - inserted} already existed).")

    await engine.dispose()
    print("\nDone. You can now:")
    print("  - Run the app:      python run.py")
    print("  - Inspect the data straight in PostgreSQL (see README.md 'View data in PostgreSQL').")


if __name__ == "__main__":
    asyncio.run(seed())
