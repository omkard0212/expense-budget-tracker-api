# Design Document: Business Expense & Budget Tracker

## Overview

This document describes the technical design for the Business Expense & Budget Tracker API built on Django REST Framework. The existing codebase already provides the three core Django models (`Department`, `CustomUser`, `Expense`) and their serializers. This design covers everything that still needs to be built: DRF settings, JWT authentication endpoints, user management endpoints, department endpoints, expense CRUD endpoints, approval workflow, budget tracking, role-based permissions, filtering, and pagination.

The system has three roles:
- **Employee** – submits and manages their own expenses
- **Manager** – approves/rejects expenses within their department; views department budget
- **Admin** – full system access over all users, departments, and expenses

All API responses use JSON. All endpoints except registration, login, and token-refresh require a valid JWT access token in the `Authorization: Bearer <token>` header.

---

## Architecture

The project follows a standard Django app structure with three apps (`users`, `departments`, `expenses`) plus the root `expense_tracker` configuration package.

```
expense_tracker/          ← project root
├── expense_tracker/      ← configuration package
│   ├── settings.py       ← add REST_FRAMEWORK + SIMPLE_JWT blocks here
│   └── urls.py           ← wire app-level url includes here
├── users/
│   ├── views.py          ← auth views + user management views
│   ├── urls.py           ← NEW: /api/auth/* and /api/users/* routes
│   └── permissions.py    ← NEW: IsAdmin, IsManagerOrAdmin custom classes
├── departments/
│   ├── views.py          ← department CRUD + budget endpoint
│   └── urls.py           ← NEW: /api/departments/* routes
└── expenses/
    ├── views.py          ← expense CRUD + approve/reject actions
    ├── urls.py           ← NEW: /api/expenses/* routes
    └── filters.py        ← NEW: ExpenseFilter (django-filter)
```

Request flow:
```
Client
  │  Authorization: Bearer <token>
  ▼
DRF Authentication Middleware  (JWTAuthentication)
  ▼
DRF Permission Classes  (IsAuthenticated + custom object/action permissions)
  ▼
View / ViewSet
  ▼
Serializer (validation + representation)
  ▼
QuerySet / DB (PostgreSQL via psycopg2)
```

---

## Components and Interfaces

### 1. Settings Additions (`expense_tracker/settings.py`)

Two new configuration blocks are appended to `settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'MAX_PAGE_SIZE': 100,
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

`rest_framework_simplejwt.token_blacklist` must also be added to `INSTALLED_APPS` to support the logout endpoint, and `python manage.py migrate` must be run afterwards.

### 2. Custom Permission Classes (`users/permissions.py`)

```python
# users/permissions.py
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    """Grants access only to users with role='Admin'."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == 'Admin')

class IsManagerOrAdmin(BasePermission):
    """Grants access to users with role='Manager' or role='Admin'."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in ('Manager', 'Admin'))
```

These classes are composed with DRF's built-in `IsAuthenticated` at the view level using `permission_classes = [IsAuthenticated, IsAdmin]` or similar.

### 3. Authentication Views (`users/views.py`)

| View class | Method | URL | Behaviour |
|---|---|---|---|
| `RegisterView` | POST | `/api/auth/register/` | `AllowAny`; creates user via `UserRegistrationSerializer`; returns 201 with `UserProfileSerializer` output |
| `LoginView` | POST | `/api/auth/login/` | `AllowAny`; delegates to `simplejwt.views.TokenObtainPairView`; returns 200 with `access` + `refresh` |
| `TokenRefreshView` | POST | `/api/auth/token/refresh/` | `AllowAny`; delegates to `simplejwt.views.TokenRefreshView`; returns 200 with new `access` |
| `LogoutView` | POST | `/api/auth/logout/` | `IsAuthenticated`; accepts `refresh` in body; calls `RefreshToken(refresh).blacklist()`; returns 205 |

`LoginView` and `TokenRefreshView` are simply re-exported from `rest_framework_simplejwt.views` — no custom code needed.

### 4. User Management Views (`users/views.py`)

| View class | Method | URL | Permission |
|---|---|---|---|
| `UserMeView` | GET | `/api/users/me/` | `IsAuthenticated` |
| `UserMeView` | PATCH | `/api/users/me/` | `IsAuthenticated` |
| `UserListView` | GET | `/api/users/` | `IsAdmin` |
| `UserDetailView` | GET / PATCH / DELETE | `/api/users/{id}/` | `IsAdmin` |

`UserMeView` uses a custom `UserUpdateSerializer` that excludes `role` from writable fields.  
`UserDetailView.destroy()` sets `is_active = False` and returns 204 (soft delete, not `instance.delete()`).

### 5. Department Views (`departments/views.py`)

```
DepartmentViewSet (ModelViewSet)
  list   → GET  /api/departments/        IsAuthenticated (all roles read)
  create → POST /api/departments/        IsAdmin
  retrieve → GET /api/departments/{id}/  IsAuthenticated
  update → PUT/PATCH /api/departments/{id}/ IsAdmin
  destroy → DELETE /api/departments/{id}/  IsAdmin

  @action(detail=True, methods=['get'], url_path='budget')
  budget → GET /api/departments/{id}/budget/   IsManagerOrAdmin
```

`get_permissions()` is overridden on the viewset to apply different permission classes per action.

The `budget` action computes:
```python
total_approved = dept.expenses.filter(status='Approved').aggregate(
    total=Sum('amount'))['total'] or Decimal('0.00')
remaining_budget = dept.budget_limit - total_approved
```

### 6. Expense Views (`expenses/views.py`)

```
ExpenseViewSet (ModelViewSet)
  list     → GET  /api/expenses/           IsAuthenticated (queryset filtered by role)
  create   → POST /api/expenses/           IsAuthenticated
  retrieve → GET  /api/expenses/{id}/      IsAuthenticated (object-level check)
  update   → PUT/PATCH /api/expenses/{id}/ IsAuthenticated (owner + Pending check)
  destroy  → DELETE /api/expenses/{id}/   IsAuthenticated (owner+Pending or Admin)

  @action(detail=True, methods=['post'], url_path='approve')
  approve → POST /api/expenses/{id}/approve/  IsManagerOrAdmin

  @action(detail=True, methods=['post'], url_path='reject')
  reject  → POST /api/expenses/{id}/reject/   IsManagerOrAdmin
```

**Role-scoped queryset** (`get_queryset`):
- Employee → `Expense.objects.filter(submitted_by=request.user)`
- Manager  → `Expense.objects.filter(Q(submitted_by=request.user) | Q(department=request.user.department))`
- Admin    → `Expense.objects.all()`

**Object-level permissions** (`check_object_permissions`):
- Retrieve: employee must own the expense; manager must own it or be in same department; admin always allowed.
- Update:   owner + status must be Pending; admin cannot update (only approve/reject/delete).
- Delete:   owner + Pending, or Admin (any status).

**`perform_create`** sets `submitted_by = request.user` and `status = 'Pending'` before save.

### 7. Expense FilterSet (`expenses/filters.py`)

```python
import django_filters
from .models import Expense

class ExpenseFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='date__gte')
    end_date   = django_filters.DateFilter(field_name='created_at', lookup_expr='date__lte')

    class Meta:
        model = Expense
        fields = ['status', 'category', 'department', 'start_date', 'end_date']
```

The `department` filter is only applied when requested by an Admin user; the view's `get_queryset` already scopes the base queryset by role, so a non-Admin's `department` filter will silently have no additional effect on their already-scoped results (which is the correct behaviour per requirements).

### 8. URL Configuration

**`users/urls.py`** (new file):
```
/api/auth/register/         → RegisterView
/api/auth/login/            → TokenObtainPairView (simplejwt)
/api/auth/token/refresh/    → TokenRefreshView (simplejwt)
/api/auth/logout/           → LogoutView
/api/users/me/              → UserMeView
/api/users/                 → UserListView
/api/users/<int:pk>/        → UserDetailView
```

**`departments/urls.py`** (new file):
```
Router.register('departments', DepartmentViewSet) → /api/departments/ + /api/departments/{id}/ + /api/departments/{id}/budget/
```

**`expenses/urls.py`** (new file):
```
Router.register('expenses', ExpenseViewSet) → /api/expenses/ + /api/expenses/{id}/ + /api/expenses/{id}/approve/ + /api/expenses/{id}/reject/
```

**`expense_tracker/urls.py`** (updated):
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('departments.urls')),
    path('api/', include('expenses.urls')),
]
```

---

## Data Models

All three models already exist. The table below summarises them and notes any constraints relevant to the API behaviour:

### `Department`

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField (PK) | |
| `name` | CharField(255) | required |
| `description` | TextField | optional (blank=True) |
| `budget_limit` | DecimalField(12,2) | required; must be positive |
| `created_at` | DateTimeField | auto_now_add |

### `CustomUser` (extends AbstractUser)

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField (PK) | |
| `username` | CharField | unique (inherited) |
| `email` | EmailField | (inherited) |
| `password` | CharField | hashed (inherited); min 8 chars enforced in serializer |
| `first_name` | CharField | (inherited) |
| `last_name` | CharField | (inherited) |
| `is_active` | BooleanField | set False on soft-delete |
| `role` | CharField(20) | choices: Admin/Manager/Employee |
| `department` | FK → Department | nullable; SET_NULL on dept delete |
| `phone` | CharField(20) | optional |

### `Expense`

| Field | Type | Notes |
|---|---|---|
| `id` | AutoField (PK) | |
| `title` | CharField(255) | required |
| `amount` | DecimalField(12,2) | required; must be > 0 |
| `category` | CharField(50) | choices: Travel/Food/Office Supplies/Other |
| `status` | CharField(20) | choices: Pending/Approved/Rejected; default Pending |
| `submitted_by` | FK → CustomUser | set to `request.user` on create |
| `department` | FK → Department | required on create |
| `description` | TextField | optional |
| `created_at` | DateTimeField | auto_now_add; used by date-range filter |
| `updated_at` | DateTimeField | auto_now |

### New/Updated Serializers

A `UserUpdateSerializer` is added to `users/serializers.py`:

```python
class UserUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH /api/users/me/ — role is excluded from writable fields."""
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone']
```

An `ExpenseCreateSerializer` is added to `expenses/serializers.py` to accept `department` as a writable FK (integer):

```python
class ExpenseCreateSerializer(serializers.ModelSerializer):
    """Used for POST /api/expenses/ — department is a writable PK field."""
    class Meta:
        model = Expense
        fields = ['title', 'amount', 'category', 'department', 'description']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
```

The existing `ExpenseSerializer` (with nested read-only representations) is used for all responses.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Role-scoped expense list isolation

*For any* authenticated user with role Employee, the list of expenses returned by `GET /api/expenses/` shall contain only expenses whose `submitted_by` equals that user — regardless of how many expenses exist in the database for other users or departments.

**Validates: Requirements 7.1**

---

### Property 2: Manager sees own and department expenses

*For any* authenticated Manager and any set of expenses in the database, every expense returned by `GET /api/expenses/` shall satisfy at least one of: `submitted_by == manager` OR `department == manager.department`.

**Validates: Requirements 7.2**

---

### Property 3: Budget remaining is always budget_limit minus approved sum

*For any* department and any set of approved expenses belonging to that department, the `remaining_budget` returned by `GET /api/departments/{id}/budget/` shall equal `budget_limit - sum(amount for expense in department.expenses if expense.status == 'Approved')`.

**Validates: Requirements 10.1, 10.2, 10.3**

---

### Property 4: Expense creation always starts as Pending

*For any* authenticated user who successfully creates an expense via `POST /api/expenses/`, the `status` field in the response shall be `'Pending'` regardless of what status value the client attempted to submit.

**Validates: Requirements 6.1**

---

### Property 5: Amount validation rejects non-positive values

*For any* request to `POST /api/expenses/` where the `amount` field is zero or any negative number, the API shall return HTTP 400 and shall not create an expense record.

**Validates: Requirements 6.2**

---

### Property 6: Only Pending expenses can be approved or rejected

*For any* expense whose `status` is `'Approved'` or `'Rejected'`, a POST request to its `/approve/` or `/reject/` endpoint shall return HTTP 400, leaving the expense status unchanged.

**Validates: Requirements 9.5**

---

### Property 7: Employee cannot modify non-Pending expenses

*For any* expense owned by an Employee where `status != 'Pending'`, a PUT or PATCH request from that Employee shall return HTTP 400 and the expense shall remain unchanged.

**Validates: Requirements 8.2**

---

### Property 8: Pagination shape invariant

*For any* list endpoint response, the JSON body shall contain exactly the keys `count`, `next`, `previous`, and `results`, where `len(results) <= page_size` and `page_size <= 100`.

**Validates: Requirements 11.1, 11.2, 11.3, 11.4**

---

### Property 9: Role field is immutable via self-update

*For any* authenticated user whose current role is R, a PATCH request to `/api/users/me/` that includes a `role` field with any value shall return HTTP 200 and the user's role in the database shall remain R.

**Validates: Requirements 3.3**

---

## Error Handling

| Scenario | HTTP Status | Body |
|---|---|---|
| Missing required field | 400 | `{"field_name": ["This field is required."]}` |
| Password < 8 chars | 400 | `{"password": ["Ensure this field has at least 8 characters."]}` |
| Duplicate username | 400 | `{"username": ["A user with that username already exists."]}` |
| Amount ≤ 0 | 400 | `{"amount": ["Amount must be greater than zero."]}` |
| Invalid category | 400 | `{"category": ['"X" is not a valid choice.']}` |
| Editing non-Pending expense | 400 | `{"detail": "Cannot edit an expense that has already been reviewed."}` |
| Approving non-Pending expense | 400 | `{"detail": "Only Pending expenses can be approved or rejected."}` |
| Invalid credentials | 401 | `{"detail": "No active account found with the given credentials"}` (simplejwt default) |
| Missing/expired token | 401 | `{"detail": "...", "code": "token_not_valid"}` (simplejwt default) |
| Insufficient role | 403 | `{"detail": "You do not have permission to perform this action."}` |
| Object not found | 404 | `{"detail": "Not found."}` |

DRF's default exception handler generates these shapes automatically for standard validation errors. Custom 400s from approval/update logic use `Response({"detail": "..."}, status=400)`.

---

## Testing Strategy

### Dual Testing Approach

Both unit/example-based tests and property-based tests are used. They complement each other: unit tests verify concrete endpoint behaviours and integration points, while property tests verify universal invariants across arbitrary generated inputs.

### Unit / Example Tests

Written with `pytest-django` and DRF's `APITestCase` (or `APIClient` with pytest fixtures). One test module per view file:

- `users/tests/test_auth.py` — registration happy path, duplicate username, short password, login success/failure, token refresh, logout blacklisting
- `users/tests/test_users.py` — profile GET/PATCH, role immutability, admin list/detail/delete, 403 for non-admins
- `departments/tests/test_departments.py` — CRUD happy paths, 403 for non-admins, 404 for missing dept, budget endpoint calculations
- `expenses/tests/test_expenses.py` — create, retrieve (role isolation), update/delete (pending vs. non-pending), approve/reject (manager dept scope, admin override)

Focus on:
- Each HTTP status code mentioned in the requirements
- Boundary conditions (amount = 0, amount = -1, amount = 0.01)
- Permission boundaries (Employee hitting admin endpoints, Manager hitting other dept)

### Property-Based Tests

**Library**: `hypothesis` with `hypothesis-django` (add `hypothesis` to `requirements.txt`).

Configured with a minimum of 100 examples per property (`@settings(max_examples=100)`).

Each property test is tagged with a comment:
```
# Feature: business-expense-budget-tracker, Property N: <property_text>
```

#### Property 1 Test — Role-scoped expense list isolation
- Generate: a set of `N` expenses (arbitrary users/departments); pick one Employee user
- Assert: `GET /api/expenses/` as that Employee returns only their own expenses
- **Feature: business-expense-budget-tracker, Property 1: Role-scoped expense list isolation**

#### Property 2 Test — Manager sees own and department expenses
- Generate: a Manager with a department; a set of expenses spread across departments
- Assert: every expense in the Manager's list satisfies `submitted_by == manager OR department == manager.department`
- **Feature: business-expense-budget-tracker, Property 2: Manager sees own and department expenses**

#### Property 3 Test — Budget remaining correctness
- Generate: a department with `budget_limit` D; N expenses with random amounts and statuses
- Assert: `remaining_budget == D - sum(approved amounts)` for any combination
- **Feature: business-expense-budget-tracker, Property 3: Budget remaining is always budget_limit minus approved sum**

#### Property 4 Test — Expense creation always starts as Pending
- Generate: valid expense payloads including ones where client tries to set `status`
- Assert: created expense always has `status == 'Pending'`
- **Feature: business-expense-budget-tracker, Property 4: Expense creation always starts as Pending**

#### Property 5 Test — Amount validation rejects non-positive values
- Generate: `amount` values ≤ 0 (integers and decimals, including -999999)
- Assert: `POST /api/expenses/` returns 400 and no new Expense row is created
- **Feature: business-expense-budget-tracker, Property 5: Amount validation rejects non-positive values**

#### Property 6 Test — Only Pending expenses can be transitioned
- Generate: expenses with `status` in `['Approved', 'Rejected']`
- Assert: `/approve/` and `/reject/` both return 400, status unchanged
- **Feature: business-expense-budget-tracker, Property 6: Only Pending expenses can be approved or rejected**

#### Property 7 Test — Employee cannot modify non-Pending expenses
- Generate: expenses owned by an Employee with status Approved or Rejected
- Assert: PATCH returns 400, expense fields unchanged
- **Feature: business-expense-budget-tracker, Property 7: Employee cannot modify non-Pending expenses**

#### Property 8 Test — Pagination shape invariant
- Generate: varying numbers of records (0 to 200) and varying `page_size` values (1–100)
- Assert: response body always has exactly keys `{count, next, previous, results}` and `len(results) <= page_size`
- **Feature: business-expense-budget-tracker, Property 8: Pagination shape invariant**

#### Property 9 Test — Role field immutability via self-update
- Generate: a user with role R; PATCH payloads containing arbitrary `role` values
- Assert: after PATCH the user's role in DB is still R and response is 200
- **Feature: business-expense-budget-tracker, Property 9: Role field is immutable via self-update**

### Test Configuration

Add to `pytest.ini` or `pyproject.toml`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = expense_tracker.settings
python_files = tests/test_*.py
python_classes = Test*
python_functions = test_*
```

Add to `requirements.txt` (dev dependencies):
```
pytest==8.3.5
pytest-django==4.10.0
hypothesis==6.135.0
```
