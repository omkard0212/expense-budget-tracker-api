# Business Expense & Budget Tracker API

A production-ready REST API built with **Django REST Framework** and **PostgreSQL** for managing business expenses, department budgets, and approval workflows. Secured with **JWT authentication** and **role-based access control**.

---

## Features

- **User Authentication with JWT** — secure login, logout with token blacklisting, and token refresh
- **Three Roles: Admin, Manager, Employee** — each role has scoped access and permissions
- **Department Management with Budget Limits** — create and manage departments with defined spending limits
- **Expense Submission and Approval Workflow** — employees submit expenses, managers/admins approve or reject
- **Real-time Budget Tracking** — view total approved spend and remaining budget per department
- **Filtering by Status, Category, and Date Range** — powerful query filters on all expense endpoints
- **Pagination on All List Endpoints** — consistent page-based pagination across the API
- **60 Automated Tests** — full test coverage across users, departments, and expenses

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10 |
| Framework | Django 5.2, Django REST Framework |
| Database | PostgreSQL |
| Authentication | SimpleJWT (JWT) |
| Filtering | django-filter |
| Environment | django-environ |

---

## API Endpoints

### Auth & Users

| Method | Endpoint | Description | Access |
|---|---|---|---|
| POST | `/api/auth/register/` | Register a new user | Public |
| POST | `/api/auth/login/` | Obtain JWT access & refresh tokens | Public |
| POST | `/api/auth/token/refresh/` | Refresh access token | Public |
| POST | `/api/auth/logout/` | Blacklist refresh token | Authenticated |
| GET | `/api/users/me/` | Get current user profile | Authenticated |
| PATCH | `/api/users/me/` | Update current user profile | Authenticated |
| GET | `/api/users/` | List all users | Admin |
| GET | `/api/users/<id>/` | Get user by ID | Admin |
| PATCH | `/api/users/<id>/` | Update user by ID | Admin |
| DELETE | `/api/users/<id>/` | Deactivate user | Admin |

### Departments

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/departments/` | List all departments | Authenticated |
| POST | `/api/departments/` | Create a department | Admin |
| GET | `/api/departments/<id>/` | Get department detail | Authenticated |
| PATCH | `/api/departments/<id>/` | Partial update department | Admin |
| PUT | `/api/departments/<id>/` | Full update department | Admin |
| DELETE | `/api/departments/<id>/` | Delete department | Admin |
| GET | `/api/departments/<id>/budget/` | View budget summary | Manager, Admin |

### Expenses

| Method | Endpoint | Description | Access |
|---|---|---|---|
| GET | `/api/expenses/` | List expenses (scoped by role) | Authenticated |
| POST | `/api/expenses/` | Submit a new expense | Authenticated |
| GET | `/api/expenses/<id>/` | Get expense detail | Owner, Manager, Admin |
| PATCH | `/api/expenses/<id>/` | Edit expense (Pending only) | Owner |
| DELETE | `/api/expenses/<id>/` | Delete expense (Pending only) | Owner, Admin |
| POST | `/api/expenses/<id>/approve/` | Approve an expense | Manager, Admin |
| POST | `/api/expenses/<id>/reject/` | Reject an expense | Manager, Admin |

### Filtering (on `GET /api/expenses/`)

| Parameter | Example |
|---|---|
| `status` | `?status=Pending` |
| `category` | `?category=Travel` |
| `department` | `?department=1` |
| `start_date` | `?start_date=2026-01-01` |
| `end_date` | `?end_date=2026-12-31` |

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/omkard0212/expense-budget-tracker-api.git
cd expense-budget-tracker-api
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root (see [Environment Variables](#environment-variables) below).

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`

---

## Environment Variables

Create a `.env` file at `D:\DRFPROJECT\expense_tracker\.env` with the following keys:

```env
SECRET_KEY=your_django_secret_key_here
DEBUG=True
DB_NAME=expense_tracker_db
DB_USER=your_postgres_username
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
```

> **Never commit your `.env` file to version control.** It is already listed in `.gitignore`.

---

## Running Tests

Run the full test suite (60 tests across all apps):

```bash
python manage.py test users departments expenses --verbosity=2
```

Run tests for a specific app:

```bash
python manage.py test users
python manage.py test departments
python manage.py test expenses
```

### Test Coverage Summary

| App | Tests | Coverage |
|---|---|---|
| `users` | 18 | Auth, registration, profile, user management |
| `departments` | 13 | CRUD, permissions, budget view |
| `expenses` | 29 | List/filter, create, edit, delete, approve/reject |
| **Total** | **60** | |

---

## Role Permissions Summary

| Action | Employee | Manager | Admin |
|---|---|---|---|
| Register / Login | ✅ | ✅ | ✅ |
| View own profile | ✅ | ✅ | ✅ |
| Submit expense | ✅ | ✅ | ✅ |
| View own expenses | ✅ | ✅ | ✅ |
| View dept expenses | ❌ | ✅ | ✅ |
| View all expenses | ❌ | ❌ | ✅ |
| Approve / Reject | ❌ | ✅ (own dept) | ✅ |
| View budget | ❌ | ✅ | ✅ |
| Manage departments | ❌ | ❌ | ✅ |
| Manage users | ❌ | ❌ | ✅ |
