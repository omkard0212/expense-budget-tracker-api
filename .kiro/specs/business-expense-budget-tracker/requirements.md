# Requirements Document

## Introduction

The Business Expense & Budget Tracker is a Django REST Framework API that enables employees to submit expense reports, managers to review and approve or reject those expenses, and administrators to manage departments, users, and monitor budget usage. The system enforces role-based access control (Admin, Manager, Employee) and tracks spending against per-department budget limits. The existing codebase provides models for `Department`, `CustomUser`, and `Expense`, along with their serializers. This specification covers all remaining implementation work: authentication endpoints, user management endpoints, department endpoints, expense CRUD endpoints, approval workflow, budget tracking, filtering, and permission enforcement.

---

## Glossary

- **API**: The Django REST Framework HTTP API exposed by this project.
- **Admin**: A `CustomUser` with `role = 'Admin'`. Has full system access.
- **Manager**: A `CustomUser` with `role = 'Manager'`. Can approve or reject expenses within their department, and view department-level budget reports.
- **Employee**: A `CustomUser` with `role = 'Employee'`. Can submit, view, update, and delete their own expenses.
- **JWT**: JSON Web Token used for stateless authentication via `djangorestframework-simplejwt`.
- **Access_Token**: Short-lived JWT used to authenticate API requests.
- **Refresh_Token**: Longer-lived JWT used to obtain a new Access_Token without re-authenticating.
- **Expense**: A single expenditure record with a title, amount, category, status, submitting user, and associated department.
- **Department**: An organisational unit with a name, description, and a `budget_limit`.
- **Budget_Limit**: The maximum total approved expense amount allowed for a department in its lifetime (or current period).
- **Status**: The approval state of an expense — one of `Pending`, `Approved`, or `Rejected`.
- **Category**: The expense classification — one of `Travel`, `Food`, `Office Supplies`, or `Other`.
- **Authenticated_User**: Any user who has presented a valid Access_Token in the `Authorization: Bearer <token>` header.
- **Permission_Denied**: An HTTP 403 response returned when an Authenticated_User attempts an action they are not authorised to perform.
- **Not_Found**: An HTTP 404 response returned when a requested resource does not exist.

---

## Requirements

### Requirement 1: User Registration

**User Story:** As a new user, I want to register an account, so that I can log in and use the expense tracking system.

#### Acceptance Criteria

1. WHEN a POST request is sent to `/api/auth/register/` with valid `username`, `email`, `password`, `first_name`, `last_name`, `role`, `department`, and `phone` fields, THE API SHALL create a new `CustomUser` and return HTTP 201 with the created user's profile data (excluding the password).
2. WHEN a POST request is sent to `/api/auth/register/` with a `password` shorter than 8 characters, THE API SHALL return HTTP 400 with a descriptive validation error.
3. WHEN a POST request is sent to `/api/auth/register/` with a `username` that already exists, THE API SHALL return HTTP 400 with a descriptive validation error.
4. WHEN a POST request is sent to `/api/auth/register/` with a missing required field (`username`, `email`, or `password`), THE API SHALL return HTTP 400 with a descriptive validation error identifying the missing field.

---

### Requirement 2: User Authentication (JWT)

**User Story:** As a registered user, I want to log in and receive JWT tokens, so that I can authenticate subsequent API requests.

#### Acceptance Criteria

1. WHEN a POST request is sent to `/api/auth/login/` with valid `username` and `password` credentials, THE API SHALL return HTTP 200 with a JSON body containing `access` and `refresh` token fields.
2. WHEN a POST request is sent to `/api/auth/login/` with invalid credentials, THE API SHALL return HTTP 401 with an error message and SHALL NOT include any token fields in the response body.
3. WHEN a POST request is sent to `/api/auth/token/refresh/` with a valid `refresh` token, THE API SHALL return HTTP 200 with a new `access` token.
4. WHEN a POST request is sent to `/api/auth/token/refresh/` with an expired or invalid `refresh` token, THE API SHALL return HTTP 401 with an error message.
5. WHEN an Authenticated_User sends a POST request to `/api/auth/logout/` with a `refresh` token in the request body, THE API SHALL attempt to blacklist the Refresh_Token and return HTTP 205 regardless of whether the token is valid or expired.

---

### Requirement 3: User Profile Management

**User Story:** As an authenticated user, I want to view and update my own profile, so that I can keep my information current.

#### Acceptance Criteria

1. WHEN an Authenticated_User sends a GET request to `/api/users/me/`, THE API SHALL return HTTP 200 with the user's profile data (id, username, email, first_name, last_name, role, department, phone).
2. WHEN an Authenticated_User sends a PATCH request to `/api/users/me/` with valid fields, THE API SHALL update the allowed profile fields (`first_name`, `last_name`, `email`, `phone`) and return HTTP 200 with the updated profile.
3. WHEN an Authenticated_User sends a PATCH request to `/api/users/me/` attempting to change their `role`, THE API SHALL ignore the `role` field and return HTTP 200 with the profile unchanged for that field.
4. IF a request is made to `/api/users/me/` without a valid Access_Token, THEN THE API SHALL return HTTP 401.

---

### Requirement 4: User Management (Admin Only)

**User Story:** As an Admin, I want to manage all user accounts, so that I can onboard employees, assign roles, and maintain the user directory.

#### Acceptance Criteria

1. WHEN an Admin sends a GET request to `/api/users/`, THE API SHALL return HTTP 200 with a paginated list of all users.
2. WHEN an Admin sends a GET request to `/api/users/{id}/`, THE API SHALL return HTTP 200 with the profile of the specified user.
3. WHEN an Admin sends a PATCH request to `/api/users/{id}/` with valid fields, THE API SHALL update the specified user's profile including `role` and `department`, and return HTTP 200.
4. WHEN an Admin sends a DELETE request to `/api/users/{id}/`, THE API SHALL deactivate (set `is_active = False`) the specified user and return HTTP 204.
5. IF a non-Admin Authenticated_User sends a request to `/api/users/` or `/api/users/{id}/` (other than their own profile), THEN THE API SHALL return HTTP 403.
6. IF a request is made to `/api/users/{id}/` where the user does not exist, THEN THE API SHALL return HTTP 404.

---

### Requirement 5: Department Management

**User Story:** As an Admin, I want to manage departments, so that I can organise teams and set budget limits.

#### Acceptance Criteria

1. WHEN an Admin sends a POST request to `/api/departments/` with valid `name`, `description`, and `budget_limit` fields, THE API SHALL create a new Department and return HTTP 201 with the created department data.
2. WHEN an Authenticated_User sends a GET request to `/api/departments/`, THE API SHALL return HTTP 200 with a list of all departments.
3. WHEN an Authenticated_User sends a GET request to `/api/departments/{id}/`, THE API SHALL return HTTP 200 with the specified department's data.
4. WHEN an Admin sends a PUT or PATCH request to `/api/departments/{id}/` with valid fields, THE API SHALL update the department and return HTTP 200 with the updated data.
5. WHEN an Admin sends a DELETE request to `/api/departments/{id}/`, THE API SHALL delete the department and return HTTP 204.
6. IF a non-Admin Authenticated_User sends a POST, PUT, PATCH, or DELETE request to `/api/departments/` or `/api/departments/{id}/`, THEN THE API SHALL return HTTP 403.
7. IF a request is made to `/api/departments/{id}/` where the department does not exist, THEN THE API SHALL return HTTP 404.
8. WHEN a POST request is sent to `/api/departments/` with a missing `name` or `budget_limit`, THE API SHALL return HTTP 400 with a descriptive validation error.

---

### Requirement 6: Expense Submission

**User Story:** As an Employee or Manager, I want to submit expense reports, so that I can request reimbursement for business expenditures.

#### Acceptance Criteria

1. WHEN an Authenticated_User sends a POST request to `/api/expenses/` with valid `title`, `amount`, `category`, `department`, and optional `description` fields, THE API SHALL create a new Expense with `status = 'Pending'`, set `submitted_by` to the requesting user, and return HTTP 201 with the created expense data.
2. WHEN a POST request is sent to `/api/expenses/` with an `amount` of zero or less, THE API SHALL return HTTP 400 with a descriptive validation error.
3. WHEN a POST request is sent to `/api/expenses/` with a `category` value not in `['Travel', 'Food', 'Office Supplies', 'Other']`, THE API SHALL return HTTP 400 with a descriptive validation error.
4. WHEN a POST request is sent to `/api/expenses/` with a missing required field (`title`, `amount`, or `category`), THE API SHALL return HTTP 400 with a descriptive validation error identifying the missing field.
5. IF a request is made to `/api/expenses/` without a valid Access_Token, THEN THE API SHALL return HTTP 401.

---

### Requirement 7: Expense Retrieval and Filtering

**User Story:** As an authenticated user, I want to list and filter expenses, so that I can review spending records relevant to my role.

#### Acceptance Criteria

1. WHEN an Employee sends a GET request to `/api/expenses/`, THE API SHALL return HTTP 200 with a paginated list containing only expenses submitted by that Employee.
2. WHEN a Manager sends a GET request to `/api/expenses/`, THE API SHALL return HTTP 200 with a paginated list of all expenses that the Manager either submitted themselves or that belong to the Manager's department.
3. WHEN an Admin sends a GET request to `/api/expenses/`, THE API SHALL return HTTP 200 with a paginated list of all expenses in the system.
4. WHEN an Authenticated_User sends a GET request to `/api/expenses/{id}/`, THE API SHALL return HTTP 200 with the expense data if the user is authorised to view it (owner, same-department Manager, or Admin).
5. IF an Authenticated_User sends a GET request to `/api/expenses/{id}/` for an expense they are not authorised to view, THEN THE API SHALL return HTTP 403.
6. WHEN an Authenticated_User provides a `status` query parameter on `/api/expenses/`, THE API SHALL return only expenses matching that status from the user's accessible set.
7. WHEN an Authenticated_User provides a `category` query parameter on `/api/expenses/`, THE API SHALL return only expenses matching that category from the user's accessible set.
8. WHEN an Authenticated_User provides `start_date` and `end_date` query parameters on `/api/expenses/`, THE API SHALL return only expenses whose `created_at` falls within the specified date range from the user's accessible set.
9. WHEN an Admin provides a `department` query parameter on `/api/expenses/`, THE API SHALL return only expenses belonging to that department, returning an empty `results` list when no matching expenses exist.

---

### Requirement 8: Expense Update and Deletion

**User Story:** As an Employee, I want to edit or delete my own pending expenses, so that I can correct mistakes before they are reviewed.

#### Acceptance Criteria

1. WHEN an Employee sends a PUT or PATCH request to `/api/expenses/{id}/` for an expense they own with `status = 'Pending'`, THE API SHALL update the allowed fields (`title`, `amount`, `category`, `description`) and return HTTP 200 with the updated expense data.
2. IF an Employee sends a PUT or PATCH request to `/api/expenses/{id}/` for an expense with `status` other than `'Pending'`, THEN THE API SHALL return HTTP 400 with a message indicating the expense cannot be edited after review.
3. IF an Employee sends a PUT or PATCH request to `/api/expenses/{id}/` for an expense they do not own, THEN THE API SHALL return HTTP 403.
4. WHEN an Employee sends a DELETE request to `/api/expenses/{id}/` for a `Pending` expense they own, THE API SHALL delete the expense and return HTTP 204.
5. IF an Employee sends a DELETE request to `/api/expenses/{id}/` for an expense that is not `Pending`, THEN THE API SHALL return HTTP 400 with an error message.
6. IF an Employee sends a DELETE request to `/api/expenses/{id}/` for an expense they do not own, THEN THE API SHALL return HTTP 403.
7. WHEN an Admin sends a DELETE request to `/api/expenses/{id}/`, THE API SHALL delete the expense regardless of status and return HTTP 204.

---

### Requirement 9: Expense Approval Workflow

**User Story:** As a Manager or Admin, I want to approve or reject submitted expenses, so that I can control departmental spending.

#### Acceptance Criteria

1. WHEN a Manager sends a POST request to `/api/expenses/{id}/approve/` for a `Pending` expense in the Manager's department, THE API SHALL set the expense `status` to `'Approved'` and return HTTP 200 with the updated expense data.
2. WHEN a Manager sends a POST request to `/api/expenses/{id}/reject/` for a `Pending` expense in the Manager's department, THE API SHALL set the expense `status` to `'Rejected'` and return HTTP 200 with the updated expense data.
3. WHEN an Admin sends a POST request to `/api/expenses/{id}/approve/` or `/api/expenses/{id}/reject/` for any `Pending` expense, THE API SHALL update the status accordingly and return HTTP 200.
4. IF a Manager sends a POST request to `/api/expenses/{id}/approve/` or `/api/expenses/{id}/reject/` for an expense that does not belong to their department, THEN THE API SHALL check the Manager's role first (handled by other rules) and return HTTP 403 for the department mismatch.
5. IF a POST request is sent to `/api/expenses/{id}/approve/` or `/api/expenses/{id}/reject/` for an expense whose `status` is not `'Pending'`, THEN THE API SHALL return HTTP 400 with an error message indicating the expense has already been reviewed.
6. IF an Employee sends a POST request to `/api/expenses/{id}/approve/` or `/api/expenses/{id}/reject/`, THEN THE API SHALL return HTTP 403.

---

### Requirement 10: Budget Tracking

**User Story:** As a Manager or Admin, I want to see a department's budget usage summary, so that I can monitor spending against the set budget limit.

#### Acceptance Criteria

1. WHEN an Authenticated_User with role Manager or Admin sends a GET request to `/api/departments/{id}/budget/`, THE API SHALL return HTTP 200 with a JSON body containing `budget_limit`, `total_approved`, and `remaining_budget` fields for that department.
2. THE Budget_Tracker SHALL calculate `total_approved` as the sum of `amount` for all Expenses in the department with `status = 'Approved'`.
3. THE Budget_Tracker SHALL calculate `remaining_budget` as `budget_limit` minus `total_approved`.
4. IF an Employee sends a GET request to `/api/departments/{id}/budget/`, THEN THE API SHALL return HTTP 403.
5. IF a GET request is sent to `/api/departments/{id}/budget/` where the department does not exist, THEN THE API SHALL return HTTP 404.

---

### Requirement 11: Pagination

**User Story:** As an API consumer, I want list endpoints to return paginated results, so that large datasets are returned in manageable chunks.

#### Acceptance Criteria

1. THE API SHALL apply pagination to all list endpoints that may return more than one record (`/api/users/`, `/api/expenses/`, `/api/departments/`).
2. WHEN a list endpoint is requested, THE API SHALL return a response body containing `count`, `next`, `previous`, and `results` fields.
3. WHEN a `page_size` query parameter is provided on a list endpoint, THE API SHALL limit the number of results per page to the specified value up to a maximum of 100.
4. WHEN no `page_size` query parameter is provided, THE API SHALL default to returning 10 results per page.

---

### Requirement 12: API Security and Authentication Enforcement

**User Story:** As a system operator, I want all API endpoints (except registration and login) to require authentication, so that unauthenticated access is prevented.

#### Acceptance Criteria

1. THE API SHALL require a valid Access_Token for all endpoints except `/api/auth/register/`, `/api/auth/login/`, and `/api/auth/token/refresh/`.
2. IF a request is made to a protected endpoint without an Authorization header, THEN THE API SHALL return HTTP 401.
3. IF a request is made to a protected endpoint with an expired or malformed Access_Token, THEN THE API SHALL return HTTP 401.
4. THE API SHALL configure `DEFAULT_AUTHENTICATION_CLASSES` to use `JWTAuthentication` from `rest_framework_simplejwt`.
5. THE API SHALL configure `DEFAULT_PERMISSION_CLASSES` to `IsAuthenticated` as the global default.
