# FastAPI Backend Architecture — Real-World Production Guide

> Complete REST API using **PyJWT** (manual JWT — no python-jose/SimpleJWT), **MySQL as default database**, all credentials via `.env`, async SQLAlchemy 2.0, Pydantic v2, and Dynamic RBAC.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Environment Setup](#environment-setup)
4. [Database Configuration](#database-configuration)
5. [Models & Schema Design](#models--schema-design)
6. [JWT Implementation (PyJWT)](#jwt-implementation-pyjwt)
7. [FastAPI Dependencies (RBAC)](#fastapi-dependencies-rbac)
8. [Authentication Routes](#authentication-routes)
9. [CRUD Routers](#crud-routers)
10. [MongoDB Integration](#mongodb-integration)
11. [App Entry Point](#app-entry-point)
12. [Database Switching Guide](#database-switching-guide)
13. [API Endpoint Summary](#api-endpoint-summary)

---

## Project Overview

- **PyJWT** for manual token creation, verification, and DB-backed blacklist
- **MySQL** as default (aiosqlite / asyncpg supported via `.env` change only)
- All secrets and DB credentials from `.env` via `pydantic-settings`
- Async SQLAlchemy 2.0 with `aiomysql` driver
- Pydantic v2 schemas, Beanie ODM for MongoDB

---

## Project Structure

```
fastapi_project/
├── app/
│   ├── main.py
│   ├── config.py                  # pydantic-settings — reads .env
│   │
│   ├── database/
│   │   ├── base.py                # async engine + session
│   │   ├── session.py             # get_db dependency
│   │   └── mongo.py               # Beanie/Motor setup
│   │
│   ├── models/                    # SQLAlchemy ORM
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   ├── token_blacklist.py
│   │   └── associations.py
│   │
│   ├── schemas/                   # Pydantic v2
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── role.py
│   │   └── permission.py
│   │
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── roles.py
│   │   └── permissions.py
│   │
│   ├── core/
│   │   ├── jwt_utils.py           # PyJWT helpers
│   │   ├── dependencies.py        # FastAPI Depends() RBAC guards
│   │   └── security.py            # password hashing
│   │
│   └── mongo_models/
│       └── activity.py
│
├── alembic/
├── tests/
├── .env
├── .env.example
├── requirements.txt
├── alembic.ini
├── run.py
└── README.md   # Complete information about setup and execution.
```

---

## Environment Setup

### requirements.txt

```txt
fastapi==0.111.1
uvicorn[standard]==0.30.1
sqlalchemy[asyncio]==2.0.31
aiomysql==0.2.0             # MySQL async driver (default)
aiosqlite==0.20.0           # SQLite async driver (optional)
asyncpg==0.29.0             # PostgreSQL async driver (optional)
alembic==1.13.2
PyJWT==2.8.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
pydantic==2.8.2
pydantic-settings==2.3.4
email-validator==2.2.0
motor==3.5.0
beanie==1.26.0
python-dotenv==1.0.1
gunicorn==22.0.0
httpx==0.27.0
pytest==8.2.2
pytest-asyncio==0.23.7
```

### .env

```env
# ─── App ─────────────────────────────────────────────────────────────────────
APP_NAME="FastAPI RBAC Service"
DEBUG=true

# ─── JWT (PyJWT) ─────────────────────────────────────────────────────────────
JWT_SECRET_KEY=change-this-jwt-secret-min-64-random-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# ─── MySQL (Default Database) ────────────────────────────────────────────────
DB_DRIVER=mysql+aiomysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fastapi_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# ─── Switch to SQLite (uncomment) ────────────────────────────────────────────
# DATABASE_URL=sqlite+aiosqlite:///./dev.db

# ─── Switch to PostgreSQL (uncomment) ────────────────────────────────────────
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fastapi_rbac_db

# ─── MongoDB ─────────────────────────────────────────────────────────────────
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=fastapi_rbac_db
# MONGO_USER=mongouser
# MONGO_PASSWORD=mongopassword

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### .env.example

```env
APP_NAME="FastAPI RBAC Service"
DEBUG=true
JWT_SECRET_KEY=changeme
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
DB_DRIVER=mysql+aiomysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fastapi_rbac_db
DB_USER=root
DB_PASSWORD=
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=fastapi_rbac_db
CORS_ORIGINS=http://localhost:3000
```

---

## Database Configuration

### app/config.py

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from datetime import timedelta
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    APP_NAME: str = "FastAPI RBAC Service"
    DEBUG:    bool = False

    # ── JWT ────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY:               str = "changeme"
    JWT_ALGORITHM:                str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS:   int = 30

    # ── Database (individual fields — assembled into URL) ──────────────────
    DB_DRIVER:   str = "mysql+aiomysql"
    DB_HOST:     str = "localhost"
    DB_PORT:     int = 3306
    DB_NAME:     str = "fastapi_rbac_db"
    DB_USER:     str = "root"
    DB_PASSWORD: str = ""

    # Optional explicit override
    DATABASE_URL: Optional[str] = None

    # ── MongoDB ────────────────────────────────────────────────────────────
    MONGO_HOST:     str = "localhost"
    MONGO_PORT:     int = 27017
    MONGO_DB:       str = "fastapi_rbac_db"
    MONGO_USER:     Optional[str] = None
    MONGO_PASSWORD: Optional[str] = None

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @computed_field
    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field
    @property
    def mongo_uri(self) -> str:
        if self.MONGO_USER and self.MONGO_PASSWORD:
            return (
                f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}"
                f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}"
            )
        return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}"

    @computed_field
    @property
    def access_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    @computed_field
    @property
    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.JWT_REFRESH_TOKEN_EXPIRE_DAYS)


settings = Settings()
```

### app/database/base.py

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=280,    # prevent MySQL "server gone away"
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(AsyncAttrs, DeclarativeBase):
    pass
```

### app/database/session.py

```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from .base import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### app/database/mongo.py

```python
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings

_client: AsyncIOMotorClient | None = None


async def connect_mongo():
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)
    from app.mongo_models.activity import UserActivity
    await init_beanie(
        database=_client[settings.MONGO_DB],
        document_models=[UserActivity],
    )


async def disconnect_mongo():
    if _client:
        _client.close()
```

---

## Models & Schema Design

### app/models/associations.py

```python
from sqlalchemy import Table, Column, Integer, ForeignKey, DateTime
from datetime import datetime
from app.database.base import Base

role_permissions = Table(
    "role_permissions", Base.metadata,
    Column("role_id",       Integer, ForeignKey("roles.id",       ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    Column("granted_at",    DateTime, default=datetime.utcnow),
)

user_roles = Table(
    "user_roles", Base.metadata,
    Column("user_id",     Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id",     Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime, default=datetime.utcnow),
)
```

### app/models/permission.py

```python
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database.base import Base


class Permission(Base):
    __tablename__ = "permissions"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    name:        Mapped[str]           = mapped_column(String(100), unique=True, nullable=False)
    resource:    Mapped[str]           = mapped_column(String(100), nullable=False)
    action:      Mapped[str]           = mapped_column(String(50),  nullable=False)
    description: Mapped[str | None]    = mapped_column(String(255))
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions", lazy="selectin"
    )
```

### app/models/role.py

```python
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.database.base import Base


class Role(Base):
    __tablename__ = "roles"

    id:          Mapped[int]        = mapped_column(Integer, primary_key=True, index=True)
    name:        Mapped[str]        = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at:  Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles", lazy="selectin"
    )
    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_roles", back_populates="roles", lazy="selectin"
    )
```

### app/models/user.py

```python
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from passlib.context import CryptContext
from datetime import datetime
from app.database.base import Base

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    username:      Mapped[str]          = mapped_column(String(80),  unique=True, nullable=False, index=True)
    email:         Mapped[str]          = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str]          = mapped_column(String(255), nullable=False)
    first_name:    Mapped[str | None]   = mapped_column(String(80))
    last_name:     Mapped[str | None]   = mapped_column(String(80))
    is_active:     Mapped[bool]         = mapped_column(Boolean, default=True)
    is_verified:   Mapped[bool]         = mapped_column(Boolean, default=False)
    created_at:    Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)
    last_login:    Mapped[datetime | None] = mapped_column(DateTime)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="user_roles", back_populates="users", lazy="selectin"
    )

    def set_password(self, plain: str):
        self.password_hash = _pwd_ctx.hash(plain)

    def verify_password(self, plain: str) -> bool:
        return _pwd_ctx.verify(plain, self.password_hash)

    def get_all_permissions(self) -> set[str]:
        perms: set[str] = set()
        for role in self.roles:
            for perm in role.permissions:
                perms.add(f"{perm.resource}:{perm.action}")
        return perms

    def has_permission(self, resource: str, action: str) -> bool:
        return f"{resource}:{action}" in self.get_all_permissions()

    def has_role(self, role_name: str) -> bool:
        return any(r.name == role_name for r in self.roles)
```

### app/models/token_blacklist.py

```python
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import select
from datetime import datetime
from app.database.base import Base


class TokenBlacklist(Base):
    """DB-backed JWT revocation — survives server restarts."""
    __tablename__ = "token_blacklist"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    jti:        Mapped[str]      = mapped_column(String(36), unique=True, nullable=False, index=True)
    token_type: Mapped[str]      = mapped_column(String(20), default="access")
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
```

---

## JWT Implementation (PyJWT)

### app/core/jwt_utils.py

```python
"""
All JWT operations use PyJWT directly.
Secret + algorithm come from settings (sourced from .env).
"""

import jwt
import uuid
from datetime import datetime, timezone
from app.config import settings


def _secret() -> str:
    return settings.JWT_SECRET_KEY


def _algorithm() -> str:
    return settings.JWT_ALGORITHM


def create_access_token(user_id: int, extra: dict = {}) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + settings.access_token_ttl
    payload = {
        "sub":  str(user_id),
        "jti":  str(uuid.uuid4()),
        "type": "access",
        "iat":  now,
        "exp":  expires,
        **extra,
    }
    return jwt.encode(payload, _secret(), algorithm=_algorithm())


def create_refresh_token(user_id: int) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + settings.refresh_token_ttl
    payload = {
        "sub":  str(user_id),
        "jti":  str(uuid.uuid4()),
        "type": "refresh",
        "iat":  now,
        "exp":  expires,
    }
    return jwt.encode(payload, _secret(), algorithm=_algorithm())


def decode_token(token: str) -> dict:
    """
    Raises:
      jwt.ExpiredSignatureError
      jwt.InvalidTokenError
    """
    return jwt.decode(token, _secret(), algorithms=[_algorithm()])


def extract_bearer(header_value: str) -> str:
    if header_value and header_value.startswith("Bearer "):
        return header_value[7:]
    return header_value or ""
```

---

## FastAPI Dependencies (RBAC)

### app/core/dependencies.py

```python
"""
FastAPI Depends()-based RBAC guards built on PyJWT.
"""

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.user           import User
from app.models.token_blacklist import TokenBlacklist
from app.core.jwt_utils        import decode_token

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials

    # ── Decode JWT ────────────────────────────────────────────────────────
    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access token required")

    # ── Check DB blacklist ────────────────────────────────────────────────
    bl_result = await db.execute(
        select(TokenBlacklist.id).where(TokenBlacklist.jti == payload["jti"])
    )
    if bl_result.scalar_one_or_none():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has been revoked")

    # ── Load user ─────────────────────────────────────────────────────────
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user   = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    return user


def require_permission(resource: str, action: str):
    """Returns a Depends-compatible checker for a specific resource:action."""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_permission(resource, action):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Forbidden — requires {resource}:{action}",
            )
        return current_user
    return checker


def require_role(*role_names: str):
    """Returns a Depends-compatible checker for role membership."""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(current_user.has_role(r) for r in role_names):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Forbidden — required roles: {', '.join(role_names)}",
            )
        return current_user
    return checker
```

---

## Authentication Routes

### app/routers/auth.py

```python
import jwt as pyjwt
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session   import get_db
from app.models.user         import User
from app.models.token_blacklist import TokenBlacklist
from app.schemas.auth        import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from app.core.jwt_utils      import (
    create_access_token, create_refresh_token,
    decode_token, extract_bearer
)
from app.core.dependencies   import get_current_user

router       = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    dup_email = await db.execute(select(User).where(User.email == payload.email))
    if dup_email.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")

    dup_user = await db.execute(select(User).where(User.username == payload.username))
    if dup_user.scalar_one_or_none():
        raise HTTPException(409, "Username already taken")

    user = User(
        username   = payload.username,
        email      = payload.email,
        first_name = payload.first_name,
        last_name  = payload.last_name,
    )
    user.set_password(payload.password)
    db.add(user)
    await db.flush()
    return {"success": True, "message": "Registered", "data": {"id": user.id, "email": user.email}}


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user   = result.scalar_one_or_none()

    if not user or not user.verify_password(payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    user.last_login = datetime.now(timezone.utc)

    extra = {
        "username":    user.username,
        "roles":       [r.name for r in user.roles],
        "permissions": list(user.get_all_permissions()),
    }
    access_token  = create_access_token(user.id, extra=extra)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
    )


@router.delete("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload    = decode_token(credentials.credentials)
        jti        = payload["jti"]
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        record     = TokenBlacklist(jti=jti, token_type="access", expires_at=expires_at)
        db.add(record)
        await db.flush()
    except pyjwt.PyJWTError:
        pass
    return {"success": True, "message": "Logged out successfully"}


@router.post("/refresh")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        token_data = decode_token(payload.refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")

    if token_data.get("type") != "refresh":
        raise HTTPException(401, "Refresh token required")

    bl = await db.execute(select(TokenBlacklist.id).where(TokenBlacklist.jti == token_data["jti"]))
    if bl.scalar_one_or_none():
        raise HTTPException(401, "Refresh token has been revoked")

    result = await db.execute(select(User).where(User.id == int(token_data["sub"])))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    extra = {
        "username":    user.username,
        "roles":       [r.name for r in user.roles],
        "permissions": list(user.get_all_permissions()),
    }
    return {"success": True, "data": {"access_token": create_access_token(user.id, extra=extra), "token_type": "Bearer"}}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    perms = current_user.get_all_permissions()
    return {
        "success": True,
        "data": {
            "id":          current_user.id,
            "username":    current_user.username,
            "email":       current_user.email,
            "roles":       [r.name for r in current_user.roles],
            "permissions": list(perms),
        },
    }
```

---

## Pydantic Schemas

### app/schemas/auth.py

```python
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username:   str      = Field(..., min_length=3, max_length=80)
    email:      EmailStr
    password:   str      = Field(..., min_length=8)
    first_name: str | None = None
    last_name:  str | None = None


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "Bearer"
```

### app/schemas/user.py

```python
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    username:   str
    email:      EmailStr
    password:   str
    first_name: str | None = None
    last_name:  str | None = None


class UserUpdate(BaseModel):
    first_name: str | None  = None
    last_name:  str | None  = None
    is_active:  bool | None = None
    password:   str | None  = None


class UserResponse(BaseModel):
    id:          int
    username:    str
    email:       str
    first_name:  str | None
    last_name:   str | None
    is_active:   bool
    roles:       list[str]
    permissions: list[str]
    created_at:  datetime
    last_login:  datetime | None

    model_config = {"from_attributes": True}
```

---

## CRUD Routers

### app/routers/users.py

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database.session   import get_db
from app.models.user         import User
from app.models.role         import Role
from app.models.token_blacklist import TokenBlacklist
from app.schemas.user        import UserCreate, UserUpdate
from app.core.dependencies   import require_permission, require_role

router = APIRouter(prefix="/users", tags=["Users"])


def _user_dict(u: User) -> dict:
    return {
        "id":          u.id,
        "username":    u.username,
        "email":       u.email,
        "first_name":  u.first_name,
        "last_name":   u.last_name,
        "is_active":   u.is_active,
        "roles":       [r.name for r in u.roles],
        "permissions": list(u.get_all_permissions()),
        "created_at":  u.created_at.isoformat(),
        "last_login":  u.last_login.isoformat() if u.last_login else None,
    }


@router.get("/")
async def list_users(
    page:     int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search:   str = Query(""),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users", "read")),
):
    q = select(User)
    if search:
        q = q.where(User.username.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    total  = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    result = await db.execute(q.offset((page - 1) * per_page).limit(per_page))
    users  = result.scalars().all()
    return {
        "success": True,
        "data": {
            "users":    [_user_dict(u) for u in users],
            "total":    total,
            "page":     page,
            "pages":    (total + per_page - 1) // per_page,
            "per_page": per_page,
        },
    }


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users", "read")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return {"success": True, "data": _user_dict(user)}


@router.post("/", status_code=201)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users", "create")),
):
    dup = await db.execute(select(User).where(User.email == payload.email))
    if dup.scalar_one_or_none():
        raise HTTPException(409, "Email already exists")
    user = User(username=payload.username, email=payload.email,
                first_name=payload.first_name, last_name=payload.last_name)
    user.set_password(payload.password)
    db.add(user)
    await db.flush()
    return {"success": True, "message": "User created", "data": _user_dict(user)}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users", "update")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data:
        user.set_password(update_data.pop("password"))
    for k, v in update_data.items():
        setattr(user, k, v)
    return {"success": True, "message": "User updated", "data": _user_dict(user)}


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("users", "delete")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    await db.delete(user)


@router.post("/{user_id}/roles")
async def assign_role(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "super_admin")),
):
    u_result = await db.execute(select(User).where(User.id == user_id))
    user     = u_result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    r_result = await db.execute(select(Role).where(Role.id == role_id))
    role     = r_result.scalar_one_or_none()
    if not role:
        raise HTTPException(404, "Role not found")

    if role not in user.roles:
        user.roles.append(role)
    return {"success": True, "data": _user_dict(user)}


@router.delete("/{user_id}/roles/{role_id}")
async def remove_role(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "super_admin")),
):
    u_result = await db.execute(select(User).where(User.id == user_id))
    user     = u_result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    r_result = await db.execute(select(Role).where(Role.id == role_id))
    role     = r_result.scalar_one_or_none()
    if role and role in user.roles:
        user.roles.remove(role)
    return {"success": True, "data": _user_dict(user)}
```

---

## MongoDB Integration

### app/mongo_models/activity.py

```python
from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional


class UserActivity(Document):
    user_id:    str
    action:     str
    resource:   Optional[str]  = None
    metadata:   dict           = Field(default_factory=dict)
    ip_address: Optional[str]  = None
    user_agent: Optional[str]  = None
    created_at: datetime       = Field(default_factory=datetime.utcnow)

    class Settings:
        name    = "user_activities"
        indexes = ["user_id", "action"]
```

---

## App Entry Point

### app/main.py

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config         import settings
from app.database.base  import engine, Base
from app.database.mongo import connect_mongo, disconnect_mongo
from app.routers        import auth, users, roles, permissions


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await connect_mongo()
    yield
    await disconnect_mongo()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api")
app.include_router(users.router,       prefix="/api")
app.include_router(roles.router,       prefix="/api")
app.include_router(permissions.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

### run.py

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## Database Switching Guide

Change only `.env`:

```env
# MySQL (default)
DB_DRIVER=mysql+aiomysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fastapi_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# SQLite
DATABASE_URL=sqlite+aiosqlite:///./dev.db

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fastapi_rbac_db
```

```bash
# MySQL: create the database first
mysql -u root -p -e "CREATE DATABASE fastapi_rbac_db CHARACTER SET utf8mb4;"

# Alembic migrations
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## API Endpoint Summary

| Method | Endpoint | Description | Guard |
|--------|----------|-------------|-------|
| POST | /api/auth/register | Register | Public |
| POST | /api/auth/login | Login → JWT | Public |
| DELETE | /api/auth/logout | Revoke token | jwt_required |
| POST | /api/auth/refresh | New access token | Public |
| GET | /api/auth/me | Current user | jwt_required |
| GET | /api/users/ | List users | permission: users:read |
| POST | /api/users/ | Create user | permission: users:create |
| GET | /api/users/{id} | Get user | permission: users:read |
| PUT | /api/users/{id} | Update user | permission: users:update |
| DELETE | /api/users/{id} | Delete user | permission: users:delete |
| POST | /api/users/{id}/roles | Assign role | role: admin |
| DELETE | /api/users/{id}/roles/{rid} | Remove role | role: admin |
| GET | /api/roles/ | List roles | permission: roles:read |
| POST | /api/roles/ | Create role | permission: roles:create |
| PUT | /api/roles/{id} | Update role | permission: roles:update |
| DELETE | /api/roles/{id} | Delete role | permission: roles:delete |
| POST | /api/roles/{id}/permissions/{pid} | Assign permission | permission: roles:update |
| DELETE | /api/roles/{id}/permissions/{pid} | Remove permission | permission: roles:update |
| GET | /api/permissions/ | List permissions | permission: permissions:read |
| POST | /api/permissions/ | Create permission | permission: permissions:create |
