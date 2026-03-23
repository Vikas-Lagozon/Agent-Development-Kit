# Full-Stack Architecture — Complete Integration Guide

> End-to-end guide combining **React.js (TypeScript)** frontend with **Flask / FastAPI / Django / Node.js (TypeScript)** backends. All using **PyJWT / jsonwebtoken** (manual JWT), **MySQL as default database**, and `.env` for every credential. Covers all flows, data contracts, error handling, and deployment.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack Matrix](#technology-stack-matrix)
3. [System Request Lifecycle](#system-request-lifecycle)
4. [Authentication Flow — End to End](#authentication-flow)
5. [JWT Token Lifecycle](#jwt-token-lifecycle)
6. [RBAC Flow — End to End](#rbac-flow)
7. [CRUD Data Flow — End to End](#crud-data-flow)
8. [API Contract — Unified Response Shapes](#api-contract)
9. [Frontend ↔ Backend Integration by Stack](#frontend--backend-integration-by-stack)
10. [Error Flow — Frontend to Backend](#error-flow)
11. [Database Layer Flow](#database-layer-flow)
12. [MongoDB Activity Log Flow](#mongodb-activity-log-flow)
13. [Environment Variables Matrix](#environment-variables-matrix)
14. [CORS Configuration Per Backend](#cors-configuration-per-backend)
15. [Deployment Architecture](#deployment-architecture)
16. [Security Hardening Checklist](#security-hardening-checklist)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            FULL-STACK APPLICATION                                │
│                                                                                  │
│  ┌─────────────────────────────┐   HTTP/HTTPS   ┌─────────────────────────────┐ │
│  │  React 18 + TypeScript      │ ◄────────────► │  Backend API (TypeScript /  │ │
│  │  Vite + React Router v6     │   JWT Bearer   │  Python)                    │ │
│  │  Zustand + Axios            │                │  Flask / FastAPI /           │ │
│  │  Tailwind / CSS Modules     │                │  Django / Node.js            │ │
│  └─────────────────────────────┘                └────────────┬────────────────┘ │
│               │                                              │                  │
│               │ localStorage                     ┌───────────┴───────────┐      │
│               │ (JWT tokens)                     │                       │      │
│        ┌──────▼──────┐                    ┌──────▼───────┐   ┌──────────▼──┐   │
│        │  Browser    │                    │  MySQL (def) │   │  MongoDB    │   │
│        │  Storage    │                    │  or SQLite / │   │  (Activity  │   │
│        └─────────────┘                    │  PostgreSQL  │   │   Logs)     │   │
│                                           └──────────────┘   └─────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Matrix

| Layer | Flask | FastAPI | Django | Node.js |
|-------|-------|---------|--------|---------|
| **Language** | Python 3.12 | Python 3.12 | Python 3.12 | TypeScript (Node 20) |
| **JWT** | PyJWT | PyJWT | PyJWT | jsonwebtoken |
| **ORM** | SQLAlchemy 2.0 | SQLAlchemy 2.0 (async) | Django ORM | Sequelize 6 |
| **Default DB** | MySQL (PyMySQL) | MySQL (aiomysql) | MySQL (mysqlclient) | MySQL (mysql2) |
| **MongoDB** | MongoEngine | Beanie (async) | MongoEngine | Mongoose |
| **Validation** | Marshmallow | Pydantic v2 | DRF Serializers | Zod (TS) |
| **Token Revoke** | DB TokenBlacklist | DB TokenBlacklist | DB TokenBlacklist | DB TokenBlacklist |
| **CORS** | flask-cors | CORSMiddleware | django-cors-headers | cors package |
| **Config** | python-decouple + .env | pydantic-settings + .env | django-environ + .env | dotenv + .env |
| **Frontend** | React 18 TypeScript | React 18 TypeScript | React 18 TypeScript | React 18 TypeScript |
| **Styling** | Tailwind or CSS Modules | Tailwind or CSS Modules | Tailwind or CSS Modules | Tailwind or CSS Modules |

---

## System Request Lifecycle

```
Browser / React App (TypeScript)
      │
      │  1. User action triggers API call
      │     e.g. usersApi.getAll() → axios.get("/users/")
      ▼
Axios Instance (src/api/axios.ts)
      │
      │  2. Request interceptor runs:
      │     token = tokenUtils.getAccess()           ← from localStorage
      │     config.headers.Authorization = `Bearer ${token}`
      ▼
      [HTTPS Network Layer]
      │
      ▼
Nginx Reverse Proxy (production)
      │
      │  3. TLS termination
      │  4. /api/* → proxied to backend server
      │  5. / → serves React /dist (SPA routing)
      ▼
Backend Server (Flask / FastAPI / Django / Node.js)
      │
      ├─ 6. jwt_required / authenticate middleware:
      │      a. Extract "Bearer " prefix from Authorization header
      │      b. jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
      │      c. Check payload["type"] == "access"
      │      d. Check TokenBlacklist.is_revoked(payload["jti"])   ← DB check
      │      e. User.objects.get(id=payload["sub"])               ← DB load
      │      f. request.user = user                               ← attach to request
      │
      ├─ 7. permission_required / authorize middleware:
      │      a. user.get_all_permissions() → {"users:read", ...}
      │      b. "users:read" ∈ permissions → proceed or 403
      │
      ├─ 8. Controller → Service → Database query (MySQL)
      │
      └─ 9. MongoDB: log activity (async / non-blocking)
      │
      │  10. JSON response built + returned
      ▼
Axios Response Interceptor (axios.ts)
      │
      ├─ 200–299: resolve promise → React state updated → re-render
      ├─ 401 + refresh token: POST /auth/refresh → retry original
      ├─ 401 + no refresh:    clearTokens() + redirect /login
      └─ 403/404/500:         toast.error(message)
      │
      ▼
Zustand Store / React Component
      │
      └─ 11. UI re-renders with new data
```

---

## Authentication Flow

### 1. Registration

```
React Register page (TypeScript — RegisterPayload type)
      │  POST /api/auth/register
      │  Body: { username, email, password, first_name, last_name }
      ▼
Backend:
      ├─ Validate input (Pydantic/Marshmallow/DRF Serializer/Zod)
      ├─ Check email uniqueness in MySQL DB
      ├─ bcrypt.hash(password, cost=12)
      ├─ INSERT INTO users ...
      └─ 201: { success: true, data: { id, email, username } }
      │
      ▼
React: toast.success("Account created!") → navigate("/login")
```

### 2. Login

```
React Login page (FormData typed via Zod + React Hook Form)
      │  POST /api/auth/login
      │  Body: { email, password }
      ▼
Backend auth service:
      ├─ User.objects.get(email=email) / User.findOne({ email })
      ├─ bcrypt.verify(password, password_hash)
      ├─ user.is_active check
      ├─ UPDATE last_login = NOW()
      │
      ├─ Collect roles from user_roles join table (MySQL)
      ├─ Collect permissions from role_permissions join table (MySQL)
      │
      ├─ PyJWT / jsonwebtoken:
      │   access_payload = {
      │     sub:         str(user.id),
      │     jti:         uuid4(),
      │     type:        "access",
      │     iat:         now,
      │     exp:         now + 1h,
      │     username:    user.username,
      │     roles:       ["admin"],
      │     permissions: ["users:read", "users:create", ...]
      │   }
      │   access_token  = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
      │   refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, ...)
      │
      └─ 200: { access_token, refresh_token, token_type: "Bearer", user: {...} }
      │
      ▼
React authStore.login():
      ├─ tokenUtils.setTokens(access_token, refresh_token) → localStorage
      ├─ set({ user, isAuthenticated: true })
      ├─ toast.success("Welcome back!")
      └─ navigate(from || "/")
```

### 3. Authenticated Request (JWT Middleware)

```
This is the decorator pattern from the project spec, implemented for each backend:

─── Flask (app/middleware/auth_middleware.py) ────────────────────────────────────
def jwt_required(func):
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return Response({"error": "Token is missing"}, 401)
        if token.startswith("Bearer "):
            token = token[7:]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user    = User.query.get(int(payload["sub"]))
            g.current_user = user         # ← attach to flask.g
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token has expired"}, 401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, 401)
        return func(*args, **kwargs)
    return wrapper

─── Django (apps/authentication/middleware.py) ───────────────────────────────────
def jwt_required(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return Response({"error": "Token is missing"}, status=401)
        if token.startswith("Bearer "):
            token = token[7:]           # remove 'Bearer ' prefix ← spec pattern
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user    = User.objects.get(id=payload["sub"])
            request.user = user         # ← attach to request (matches spec)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token has expired"}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=401)
        return func(self, request, *args, **kwargs)
    return wrapper

─── FastAPI (app/core/dependencies.py) ───────────────────────────────────────────
async def get_current_user(credentials = Depends(bearer_scheme), db = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    user = await db.execute(select(User).where(User.id == int(payload["sub"])))
    return user.scalar_one_or_none()

─── Node.js TypeScript (src/middleware/authenticate.ts) ──────────────────────────
export async function authenticate(req, res, next) {
  const token = extractBearer(req.headers.authorization);
  if (!token) { res.status(401).json({ error: "Token is missing" }); return; }
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET) as JwtPayload;
    const user    = await User.findByPk(parseInt(payload.sub), { include: ["roles"] });
    req.user      = user;     // ← attach to request
    next();
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) res.status(401).json({ error: "Token has expired" });
    else res.status(401).json({ error: "Invalid token" });
  }
}
```

### 4. Token Refresh

```
React Axios interceptor detects 401:
      │
      ├─ originalRequest._retry already set? → reject (prevent infinite loop)
      ├─ Set isRefreshing = true
      │
      │  POST /api/auth/refresh
      │  Body: { refresh_token: "eyJ..." }
      ▼
Backend:
      ├─ jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=["HS256"])
      ├─ Check payload["type"] == "refresh"
      ├─ TokenBlacklist.is_revoked(payload["jti"]) → false check
      ├─ Load user from MySQL DB
      ├─ Build new access token with fresh permissions from DB
      └─ 200: { access_token: "eyJ..." }
      │
      ▼
React:
      ├─ tokenUtils.setTokens(newToken)         → update localStorage
      ├─ processQueue(null, newToken)            → retry all queued requests
      └─ originalRequest retried automatically   → user sees no interruption
```

### 5. Logout

```
React: user clicks Sign Out
      │  DELETE /api/auth/logout
      │  Authorization: Bearer <access_token>
      ▼
Backend:
      ├─ Extract JTI from access token payload
      ├─ TokenBlacklist.revoke(jti, "access", expires_at)  ← MySQL INSERT
      └─ 200: { message: "Logged out" }
      │
      ▼
React:
      ├─ tokenUtils.clearTokens()      → remove from localStorage
      ├─ set({ user: null, isAuthenticated: false })
      └─ navigate("/login")

Server-side effect:
      Even if the old token is presented again, the JWT middleware checks
      TokenBlacklist.is_revoked(jti) → true → 401 Unauthorized
      This is DB-backed so it survives server restarts.
```

---

## JWT Token Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       JWT TOKEN LIFECYCLE                                │
│                                                                          │
│  LOGIN                                                                   │
│    │                                                                     │
│    ├──► ACCESS TOKEN (TTL: 1 hour)                                       │
│    │       Stored:   localStorage (key from .env VITE_TOKEN_KEY)         │
│    │       Sent:     Authorization: Bearer <token> on every request      │
│    │       Payload:  { sub, jti, type:"access", roles, permissions }     │
│    │       Secret:   JWT_SECRET_KEY (from .env)                          │
│    │                                                                     │
│    └──► REFRESH TOKEN (TTL: 30 days)                                     │
│             Stored:  localStorage (VITE_REFRESH_TOKEN_KEY)               │
│             Sent:    Only to POST /auth/refresh                          │
│             Payload: { sub, jti, type:"refresh" }                        │
│             Secret:  JWT_SECRET_KEY (Flask/FastAPI/Django) or            │
│                      JWT_REFRESH_SECRET (Node.js — separate secret)      │
│                                                                          │
│  NORMAL REQUEST (< 1h after login)                                       │
│    Access token valid → backend decodes → proceeds normally              │
│                                                                          │
│  AFTER 1h (access token expired)                                         │
│    Backend returns 401                                                   │
│    Axios interceptor: POST /auth/refresh with refresh token              │
│    New access token → stored → original request retried seamlessly       │
│                                                                          │
│  AFTER 30 days (refresh token expired)                                   │
│    Refresh endpoint returns 401                                          │
│    Axios interceptor: clearTokens() → window.location = /login           │
│                                                                          │
│  LOGOUT (before expiry)                                                  │
│    JTI added to TokenBlacklist in MySQL (survives restarts)              │
│    Token rejected server-side even if not expired                        │
│    Both tokens removed from localStorage                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## RBAC Flow

### Database Entities (MySQL, all backends)

```
permissions
  id | name          | resource | action
  ───┼───────────────┼──────────┼───────
  1  | users:read    | users    | read
  2  | users:create  | users    | create
  3  | roles:read    | roles    | read

roles
  id | name
  ───┼────────────
  1  | super_admin
  2  | admin
  3  | viewer

role_permissions  (junction)
  role_id | permission_id
  ────────┼──────────────
  1       | 1, 2, 3       (super_admin → all)
  2       | 1, 2, 3       (admin → read+create users, read roles)
  3       | 1, 3          (viewer → read only)

users
  id | username | email
  1  | alice    | alice@acme.com

user_roles  (junction)
  user_id | role_id
  1       | 2            (alice is admin)
```

### RBAC Check Flow

```
API Request: DELETE /api/users/5
Required permission: users:delete

Step 1: jwt_required middleware decodes token
        payload["sub"] = "1"  →  user = alice

Step 2: permission_required("users", "delete") / authorize("users", "delete")
        alice.user_roles  → [admin]
        admin.role_perms  → [users:read, users:create, roles:read]
        "users:delete" ∈ {users:read, users:create, roles:read} → FALSE
        → 403 Forbidden

API Request: GET /api/users
Required permission: users:read

        alice.user_roles  → [admin]
        "users:read" ∈ {users:read, users:create, roles:read} → TRUE
        → 200 OK
```

### Frontend RBAC Rendering

```
User alice (admin) logs in:
  JWT payload contains: permissions: ["users:read","users:create","roles:read"]

authStore.user.permissions = ["users:read","users:create","roles:read"]

React renders Sidebar:
  <PermissionGate resource="users" action="read">
      hasPermission("users","read") → true  → shows Users link ✅

  <PermissionGate resource="permissions" action="read">
      hasPermission("permissions","read") → false → hidden ❌

React renders UserList row:
  <PermissionGate resource="users" action="update">
      → renders Edit button ✅

  <PermissionGate resource="users" action="delete">
      → hidden ❌ (not in alice's permissions)

Route guard:
  <PermissionRoute resource="users" action="delete">
      → redirects to /403 if alice tries to access /users/delete
```

---

## CRUD Data Flow

### Create Flow

```
React UserForm (TypeScript — UserCreate type, Zod-validated)
      │  handleSubmit(onSubmit) → usersApi.create(data)
      │  POST /api/users/
      │  Authorization: Bearer <access_token>
      │  Body: { username, email, password, first_name, last_name }
      ▼
Backend RBAC check: users:create → ✅
Backend validation: Pydantic/Marshmallow/DRF Serializer/Zod
Backend Service:
      ├─ Check email uniqueness (MySQL SELECT)
      ├─ bcrypt.hash(password)
      ├─ INSERT INTO users (MySQL)
      ├─ COMMIT transaction
      └─ MongoDB: UserActivity.insert({ action: "create_user", user_id: ... })
Backend: 201 { success: true, data: { id, username, email, ... } }
      │
      ▼
React:
      ├─ toast.success("User created")
      └─ navigate("/users")
```

### Read Flow (Paginated)

```
React UserList mounts:
      │  usePagination<User>(usersApi.getAll, {}, "users")
      │  GET /api/users/?page=1&per_page=10&search=
      ▼
Backend: 200 {
  success: true,
  data: {
    users:    [...],
    total:    53,
    page:     1,
    pages:    6,
    per_page: 10
  }
}
      │
      ▼
React:
      ├─ setData(users)   — typed as User[] from TypeScript
      ├─ setPagination({ total:53, page:1, pages:6, perPage:10 })
      └─ Renders table + pagination controls

User types in search box:
      │  handleSearch("alice")
      │  GET /api/users/?page=1&per_page=10&search=alice
      └─ Table updates (filtered by username ILIKE %alice% in MySQL)
```

### Update Flow

```
React UserForm (pre-filled via usersApi.getOne(id)):
      ├─ reset(form) with existing user data
      ├─ User modifies fields → submit
      │  PUT /api/users/:id
      │  Body: { first_name, last_name, is_active }  (password only if changed)
      ▼
Backend:
      ├─ RBAC: users:update → ✅
      ├─ Find user by id (404 if missing)
      ├─ UPDATE users SET ... WHERE id = :id
      └─ 200 { success: true, data: { updated user } }
      │
      ▼
React:
      ├─ toast.success("User updated")
      └─ navigate("/users")
```

### Delete Flow

```
React: PermissionGate(users:delete) wraps Delete button
      ├─ window.confirm("Delete alice?")
      │  DELETE /api/users/1
      ▼
Backend:
      ├─ RBAC: users:delete → ✅
      ├─ DELETE FROM users WHERE id = 1  (CASCADE deletes user_roles rows)
      └─ 204 No Content
      │
      ▼
React:
      ├─ setItems(prev => prev.filter(u => u.id !== 1))
      └─ toast.success("User deleted")
```

---

## API Contract

### Unified Response Envelope (all backends)

```json
// Success — list with pagination
{
  "success": true,
  "message": "Success",
  "data": {
    "users":    [...],
    "total":    53,
    "page":     1,
    "pages":    6,
    "per_page": 10
  }
}

// Success — single item
{
  "success": true,
  "message": "User created",
  "data": {
    "id":          1,
    "username":    "alice",
    "email":       "alice@acme.com",
    "first_name":  "Alice",
    "last_name":   "Smith",
    "is_active":   true,
    "roles":       ["admin"],
    "permissions": ["users:read", "users:create", "roles:read"],
    "created_at":  "2024-01-01T00:00:00Z",
    "last_login":  "2024-07-10T08:00:00Z"
  }
}

// Login success
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token":  "eyJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
    "token_type":    "Bearer",
    "user":          { ... }
  }
}

// Error — generic
{
  "success": false,
  "message": "Permission denied: users:delete",
  "errors":  null
}

// Error — validation
{
  "success": false,
  "message": "Validation error",
  "errors": {
    "email":    ["Invalid email format"],
    "password": ["Must be at least 8 characters"]
  }
}
```

---

## Frontend ↔ Backend Integration by Stack

### React TypeScript + Flask

```
Axios baseURL:   http://localhost:5000/api
No trailing slash on Flask routes (unlike Django)

Login URL:       POST http://localhost:5000/api/auth/login
Refresh URL:     POST http://localhost:5000/api/auth/refresh
Logout URL:      DELETE http://localhost:5000/api/auth/logout

Response shape:  { success, message, data }  ← nested data key
usersApi.getAll  → response.data.data.users   ← two levels deep

Validation errs: { success: false, message: "...", errors: null }
Auth errs:       { error: "Token has expired" }   ← note: "error" not "message"
                 Normalize in extractError() utility
```

### React TypeScript + FastAPI

```
Axios baseURL:   http://localhost:8000/api
Auto-docs:       http://localhost:8000/docs  (Swagger)

Pydantic 422:    { detail: [{ loc, msg, type }] }
                 Handle 422 same as 400 in error interceptor

Async all the way: aiomysql → async SQLAlchemy → FastAPI async routes
Response shape:  { success, message, data }  ← same as Flask
```

### React TypeScript + Django

```
Axios baseURL:    http://localhost:8000/api
TRAILING SLASH:   Django requires trailing slash on all URLs!
                  usersApi: api.get("/users/")  ← must include slash

Login URL:        POST http://localhost:8000/api/auth/login/
Refresh URL:      POST http://localhost:8000/api/auth/refresh/

DRF validation errors (non-standard):
  { "email": ["This field is required."] }   ← not nested in "errors"
  Normalize with extractError():
  const errs = Object.values(err.response?.data || {}).flat().join(", ")

Pagination (if using DRF standard):
  { count, next, previous, results }
  Map to our standard shape:
  { users: results, total: count, page: 1, pages: Math.ceil(count/10) }
```

### React TypeScript + Node.js TypeScript

```
Axios baseURL:   http://localhost:3000/api
No trailing slash on Express routes

JWT: access uses JWT_SECRET, refresh uses JWT_REFRESH_SECRET (separate!)
     Axios refresh call sends to /auth/refresh with refresh_token in body.
     Both secrets must be in .env (never hardcoded).

Sequelize errs:  { success: false, message: "Validation error", errors: [...] }
Mongoose errs:   { success: false, message: "..." }

TypeScript types shared convention:
  Both frontend and backend define the same User/Role/Permission interfaces.
  Consider a shared types package (nx monorepo / shared tsconfig path).
```

### Normalizing Backend Differences in Axios (TypeScript)

```typescript
// src/utils/apiError.ts
export function extractError(err: unknown): string {
  const e = err as any;
  if (e.response?.data?.message) return e.response.data.message;
  if (e.response?.data?.detail) {
    // FastAPI Pydantic errors
    if (Array.isArray(e.response.data.detail)) {
      return e.response.data.detail.map((d: any) => d.msg).join(", ");
    }
    return String(e.response.data.detail);
  }
  if (e.response?.data?.errors) {
    const errs = e.response.data.errors;
    if (typeof errs === "object") {
      return Object.values(errs).flat().join(", ");
    }
  }
  if (e.response?.data?.error) return e.response.data.error;
  if (e.message === "Network Error") return "Cannot reach server";
  return "An unexpected error occurred";
}

// src/utils/normalizeResponse.ts
export function normalizeListResponse<T>(
  response: any, listKey: string = "users"
): { items: T[]; total: number; page: number; pages: number; perPage: number } {
  const raw = response?.data?.data ?? response?.data;
  if (!raw) return { items: [], total: 0, page: 1, pages: 1, perPage: 10 };

  // Standard shape (Flask/FastAPI/Node.js)
  if (raw[listKey] !== undefined) {
    return { items: raw[listKey], total: raw.total, page: raw.page, pages: raw.pages, perPage: raw.per_page };
  }

  // Django DRF default pagination
  if (raw.results !== undefined) {
    return { items: raw.results, total: raw.count, page: 1, pages: Math.ceil(raw.count / 10), perPage: 10 };
  }

  if (Array.isArray(raw)) return { items: raw, total: raw.length, page: 1, pages: 1, perPage: raw.length };
  return { items: [], total: 0, page: 1, pages: 1, perPage: 10 };
}
```

---

## Error Flow

```
Backend throws error
      │
      ├─ 400 Bad Request       → Missing required field
      ├─ 401 Unauthorized      → Token missing / expired / revoked
      ├─ 403 Forbidden         → Authenticated but wrong permission/role
      ├─ 404 Not Found         → Resource doesn't exist in MySQL
      ├─ 409 Conflict          → Duplicate email/username
      ├─ 422 Unprocessable     → Schema validation failed (FastAPI/DRF)
      └─ 500 Internal Server   → Unhandled exception
      │
      ▼
Axios Response Interceptor (src/api/axios.ts)
      │
      ├─ 401 + refresh token exists → POST /auth/refresh → retry queued requests
      ├─ 401 + no refresh →         tokenUtils.clearTokens() + redirect /login
      ├─ 403 → pass through to calling code → toast.error("Access denied")
      ├─ 404 → pass through → component shows "Not found" state
      ├─ 409 → pass through → form shows "Email already exists"
      ├─ 422 → pass through → form shows field errors
      └─ 500 → toast.error("Server error. Please try again.")
      │
      ▼
React Component (try/catch in useCrud / usePagination / direct call)
      │
      ├─ extractError(err)   → human-readable message
      ├─ toast.error(msg)    → toast notification
      └─ setError(err)       → optional inline error state
```

---

## Database Layer Flow

### MySQL Schema (identical across all backends)

```sql
-- MySQL default, created by ORM migrations

CREATE TABLE users (
  id            INT          PRIMARY KEY AUTO_INCREMENT,
  username      VARCHAR(80)  NOT NULL UNIQUE,
  email         VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  first_name    VARCHAR(80),
  last_name     VARCHAR(80),
  is_active     BOOLEAN      DEFAULT TRUE,
  is_verified   BOOLEAN      DEFAULT FALSE,
  created_at    DATETIME     DEFAULT NOW(),
  updated_at    DATETIME     DEFAULT NOW() ON UPDATE NOW(),
  last_login    DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE permissions (
  id          INT          PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(100) NOT NULL UNIQUE,
  resource    VARCHAR(100) NOT NULL,
  action      VARCHAR(50)  NOT NULL,
  description VARCHAR(255),
  created_at  DATETIME     DEFAULT NOW(),
  UNIQUE KEY uq_resource_action (resource, action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE roles (
  id          INT          PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(100) NOT NULL UNIQUE,
  description VARCHAR(255),
  created_at  DATETIME     DEFAULT NOW(),
  updated_at  DATETIME     DEFAULT NOW() ON UPDATE NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE role_permissions (
  role_id       INT  NOT NULL REFERENCES roles(id)       ON DELETE CASCADE,
  permission_id INT  NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  granted_at    DATETIME DEFAULT NOW(),
  PRIMARY KEY (role_id, permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_roles (
  user_id     INT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id     INT  NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  assigned_at DATETIME DEFAULT NOW(),
  PRIMARY KEY (user_id, role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE token_blacklist (
  id         INT         PRIMARY KEY AUTO_INCREMENT,
  jti        VARCHAR(36) NOT NULL UNIQUE,
  token_type VARCHAR(20) DEFAULT 'access',
  revoked_at DATETIME    DEFAULT NOW(),
  expires_at DATETIME    NOT NULL,
  INDEX idx_jti (jti)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Database Switching (change .env only)

```env
# ── MySQL (default for all backends) ─────────────────────────────────────────
DB_DRIVER=mysql+pymysql      # Flask
DB_DRIVER=mysql+aiomysql     # FastAPI
DB_ENGINE=django.db.backends.mysql   # Django
DB_DIALECT=mysql             # Node.js

# ── SQLite (development) ──────────────────────────────────────────────────────
DATABASE_URL=sqlite:///dev.db          # Flask
DATABASE_URL=sqlite+aiosqlite:///./dev.db  # FastAPI
DB_ENGINE=django.db.backends.sqlite3   # Django
DB_DIALECT=sqlite                      # Node.js

# ── PostgreSQL (production alternative) ───────────────────────────────────────
DATABASE_URL=postgresql://u:p@localhost/db   # Flask
DATABASE_URL=postgresql+asyncpg://u:p@localhost/db  # FastAPI
DB_ENGINE=django.db.backends.postgresql  # Django
DB_DIALECT=postgres                      # Node.js
```

```bash
# MySQL: always create the database first
mysql -u root -p -e "CREATE DATABASE rbac_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Then run migrations
flask db upgrade           # Flask
alembic upgrade head       # FastAPI
python manage.py migrate   # Django
npm run migrate            # Node.js (Sequelize)
```

---

## MongoDB Activity Log Flow

```
User performs any action (all backends)
      │
      ├─ SQL DB (MySQL): primary data operation (ACID guaranteed)
      │
      └─ MongoDB: flexible audit log (non-blocking)
         UserActivity.insert({
           user_id:    "42",
           action:     "login",           # or create_user | update_user | delete_user
           resource:   "users",
           metadata:   { target_id: 99, email: "bob@..." },
           ip_address: "192.168.1.1",
           created_at: ISODate()
         })

MongoDB used for:
  ✅ Audit logs (who did what, when)
  ✅ Login/logout history with IP + user-agent
  ✅ Flexible per-action metadata (schema varies by action type)
  ✅ Event sourcing / compliance reporting

MySQL used for:
  ✅ Users, Roles, Permissions (structured relational data)
  ✅ RBAC join tables (user_roles, role_permissions)
  ✅ Token blacklist (requires ACID: no duplicate JTIs)
  ✅ Any data requiring transactions or foreign keys
```

---

## Environment Variables Matrix

| Variable | React (Vite) | Flask | FastAPI | Django | Node.js |
|----------|-------------|-------|---------|--------|---------|
| API URL | `VITE_API_BASE_URL` | — | — | — | — |
| App Secret | — | `SECRET_KEY` | — | `SECRET_KEY` | — |
| JWT Access Secret | — | `JWT_SECRET_KEY` | `JWT_SECRET_KEY` | `JWT_SECRET_KEY` | `JWT_SECRET` |
| JWT Refresh Secret | — | (same key) | (same key) | (same key) | `JWT_REFRESH_SECRET` |
| JWT Access TTL | — | `JWT_ACCESS_TOKEN_EXPIRES` | `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` | `JWT_ACCESS_EXPIRES_IN` |
| JWT Refresh TTL | — | `JWT_REFRESH_TOKEN_EXPIRES` | `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `JWT_REFRESH_TOKEN_EXPIRE_SECONDS` | `JWT_REFRESH_EXPIRES_IN` |
| DB Host | — | `DB_HOST` | `DB_HOST` | `DB_HOST` | `DB_HOST` |
| DB Port | — | `DB_PORT` | `DB_PORT` | `DB_PORT` | `DB_PORT` |
| DB Name | — | `DB_NAME` | `DB_NAME` | `DB_NAME` | `DB_NAME` |
| DB User | — | `DB_USER` | `DB_USER` | `DB_USER` | `DB_USER` |
| DB Pass | — | `DB_PASSWORD` | `DB_PASSWORD` | `DB_PASSWORD` | `DB_PASSWORD` |
| DB Driver | — | `DB_DRIVER` | `DB_DRIVER` | `DB_ENGINE` | `DB_DIALECT` |
| MongoDB Host | — | `MONGO_HOST` | `MONGO_HOST` | `MONGO_HOST` | `MONGO_HOST` |
| MongoDB Port | — | `MONGO_PORT` | `MONGO_PORT` | `MONGO_PORT` | `MONGO_PORT` |
| MongoDB DB | — | `MONGO_DB` | `MONGO_DB` | `MONGO_DB` | `MONGO_DB` |
| CORS Origins | — | `CORS_ORIGINS` | `CORS_ORIGINS` | `CORS_ALLOWED_ORIGINS` | `CORS_ORIGIN` |
| Port | — | `PORT` | `PORT` | — | `PORT` |
| Debug | — | `FLASK_ENV` | `DEBUG` | `DJANGO_ENV` | `NODE_ENV` |

---

## CORS Configuration Per Backend

### Flask

```python
# app/__init__.py — values from .env via config
from flask_cors import CORS
CORS(app, resources={
    r"/api/*": {
        "origins":             app.config["CORS_ORIGINS"],  # list from .env
        "methods":             ["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
        "allow_headers":       ["Content-Type", "Authorization"],
        "supports_credentials": True,
    }
})
```

### FastAPI

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,   # list from .env via pydantic-settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Django

```python
# config/settings/base.py
CORS_ALLOWED_ORIGINS  = env.list("CORS_ALLOWED_ORIGINS")  # from .env
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS     = ["authorization", "content-type", "accept"]
```

### Node.js (TypeScript)

```typescript
// src/app.ts
import cors from "cors";
app.use(cors({
  origin:         env.CORS_ORIGIN,       // string[] from .env
  credentials:    true,
  methods:        ["GET","POST","PUT","PATCH","DELETE","OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"],
}));
```

---

## Deployment Architecture

### Docker Compose — Full Stack

```yaml
version: "3.9"

services:
  frontend:
    build:
      context:    ./react_project
      args:
        VITE_API_BASE_URL: /api
    ports:        ["80:80"]
    depends_on:   [backend]

  backend:
    build:        ./backend_project
    ports:        ["8000:8000"]
    env_file:     ./.env.production   # ← all secrets from .env file
    depends_on:   [mysql, mongo]

  mysql:
    image:        mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE:      ${DB_NAME}
    volumes:      [mysql_data:/var/lib/mysql]
    ports:        ["3306:3306"]

  mongo:
    image:        mongo:7-jammy
    volumes:      [mongo_data:/data/db]
    ports:        ["27017:27017"]

  nginx:
    image:        nginx:alpine
    ports:        ["443:443", "80:80"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:   [frontend, backend]

volumes:
  mysql_data:
  mongo_data:
```

### Nginx Config

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    root  /var/www/dist;   # React build
    index index.html;

    # SPA routing — React Router
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass         http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        limit_req          zone=api_limit burst=20 nodelay;
    }

    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}
```

### React Dockerfile (TypeScript build)

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build    # runs: tsc && vite build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Security Hardening Checklist

### JWT & Auth
- [ ] `JWT_SECRET_KEY` minimum 64 random characters, generated with `openssl rand -hex 32`
- [ ] Node.js uses separate `JWT_REFRESH_SECRET` from `JWT_SECRET` (two independent keys)
- [ ] Access token TTL ≤ 1 hour, refresh token TTL ≤ 30 days
- [ ] All passwords hashed with bcrypt, cost factor ≥ 12
- [ ] `TokenBlacklist` backed by MySQL (not in-memory — survives restarts)
- [ ] `jti` (JWT ID) unique per token, stored in blacklist on logout
- [ ] `type` claim validated ("access" vs "refresh") to prevent token type confusion

### Backend
- [ ] All secrets in `.env` — never committed to git (`.env` in `.gitignore`)
- [ ] `.env.example` committed with placeholder values only
- [ ] RBAC enforced server-side on every endpoint — never trust client claims
- [ ] SQL injection prevented by ORM parameterized queries
- [ ] MongoDB injection prevented by ODM validators (MongoEngine/Beanie/Mongoose)
- [ ] Rate limiting on auth endpoints (login: 5/15min, register: 3/15min)
- [ ] `password_hash` / `passwordHash` never included in API responses (`to_dict()` excludes it)
- [ ] HTTPS only in production (Nginx HTTP→HTTPS redirect)
- [ ] Error messages in production never expose stack traces

### Frontend (TypeScript)
- [ ] All API calls through typed Axios instance — no raw `fetch()`
- [ ] `tokenUtils` centrally manages localStorage reads/writes
- [ ] Token refresh interceptor queues requests (prevents multiple simultaneous refreshes)
- [ ] `PermissionGate` used for all conditional UI rendering
- [ ] `PermissionRoute` guards all RBAC-restricted routes
- [ ] `fetchMe()` called on app load to sync permissions from server
- [ ] Zod schemas validate all form inputs before submission
- [ ] TypeScript strict mode — `noImplicitAny`, `strictNullChecks` enabled
- [ ] `VITE_*` env vars only — secrets never exposed to the frontend bundle

### Database
- [ ] MySQL user has minimal privileges (SELECT/INSERT/UPDATE/DELETE only — no DROP)
- [ ] MySQL `utf8mb4` charset for full Unicode support
- [ ] Database credentials only in `.env` — never hardcoded
- [ ] Regular backups (daily minimum for production)
- [ ] MongoDB connection string in `.env`, Atlas IP whitelist in production

### DevOps
- [ ] Docker secrets or vault for sensitive env variables in production
- [ ] Nginx rate limiting configured at reverse proxy level
- [ ] SSL certificates auto-renewed (Let's Encrypt / Certbot)
- [ ] Container images scanned for vulnerabilities before deployment
- [ ] Health check endpoints (`/health`) for load balancer / uptime monitoring

---

## Quick Start — All Stacks

```bash
# 1. Start databases
docker run -d --name mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  -e MYSQL_DATABASE=rbac_db \
  -p 3306:3306 mysql:8.0

docker run -d --name mongo -p 27017:27017 mongo:7

# 2. Backend (choose one)

## Flask
cd backend_flask
pip install -r requirements.txt
cp .env.example .env    # edit DB_PASSWORD etc.
flask db upgrade
python run.py           # → http://localhost:5000

## FastAPI
cd backend_fastapi
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python run.py           # → http://localhost:8000/docs

## Django
cd backend_django
pip install -r requirements/base.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_rbac
python manage.py runserver 0.0.0.0:8000

## Node.js (TypeScript)
cd backend_nodejs
npm install
cp .env.example .env
npm run migrate
npm run dev             # → http://localhost:3000

# 3. Frontend (TypeScript)
cd react_project
npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000/api
npm run dev            # → http://localhost:3000 (or 5173 with Vite default)
```

### Default Seed Credentials

```
Email:    admin@example.com
Password: Admin@123
Role:     super_admin
Perms:    all permissions
```
