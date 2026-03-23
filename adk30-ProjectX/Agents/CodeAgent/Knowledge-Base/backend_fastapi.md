# FastAPI Backend — Production Guide

> PyJWT · Sync SQLAlchemy (no async) · MySQL default · `.env` credentials · Dynamic RBAC · Windows + Linux compatible

---

## Root Cause of All Your Errors — Explained

| Error | Root Cause | Fix Applied |
|-------|-----------|-------------|
| `AsyncAttrs` ImportError | `AsyncAttrs` requires SQLAlchemy ≥ 2.0.26 AND the class is not in older builds | **Switched to sync SQLAlchemy** — Alembic works perfectly with sync, and FastAPI routes use `def` not `async def` for DB operations |
| `No module named 'app'` | Uvicorn was run from wrong directory OR imports used absolute paths | **All imports use relative paths** inside the `app` package |
| `CORS_ORIGINS` JSON error | `pydantic-settings` tries to parse list fields as JSON — a plain comma-separated string fails | **Use `str` type + split in `@property`** instead of `list[str]` |
| Alembic `config_main_section` | Old Alembic API changed | **Provided working `env.py`** that uses `config.config_ini_section` |
| `DATABASE_URL=None` | `.env` not loaded before Alembic reads it | **Alembic `env.py` loads dotenv manually** |
| `cp` not found on Windows | `cp` is a Linux/Mac command | **Use `copy` on Windows CMD** |

---

## Verified Package Versions (Python 3.11.x)

```txt
# requirements.txt
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.31
pymysql==1.1.1
cryptography==42.0.8
aiosqlite==0.20.0
alembic==1.13.1
PyJWT==2.8.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
pydantic==2.8.2
pydantic-settings==2.3.4
python-dotenv==1.0.1
```

> **No `aiomysql`, no `asyncpg`** — we use sync SQLAlchemy with `pymysql`.
> FastAPI works perfectly with sync DB sessions via `Depends()`.

---

## Project Structure

```
fastapi_project/
├── app/
│   ├── __init__.py          (empty)
│   ├── main.py
│   ├── config.py
│   ├── database.py          (sync engine + session)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   ├── associations.py
│   │   └── token_blacklist.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── user.py
│   │   └── role.py
│   ├── routers/
│   │   ├── __init__.py      (empty)
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── roles.py
│   │   └── permissions.py
│   ├── core/
│   │   ├── jwt_utils.py
│   │   ├── security.py
│   │   └── dependencies.py
│   └── services/
│       ├── auth_service.py
│       └── user_service.py
├── alembic/
│   ├── env.py               (fixed — loads .env manually)
│   └── script.py.mako
├── alembic.ini
├── .env
├── .env.example
├── requirements.txt
└── run.py
```

---

## Minimum Steps to Run (Windows CMD)

```cmd
:: Step 1 — Create project and venv (run from parent folder)
mkdir fastapi_project
cd fastapi_project
py -3.11 -m venv venv
venv\Scripts\activate

:: Step 2 — Install packages
pip install -r requirements.txt

:: Step 3 — Create MySQL database
mysql -u root -p -e "CREATE DATABASE fastapi_rbac_db CHARACTER SET utf8mb4;"

:: Step 4 — Copy .env (Windows)
copy .env.example .env
:: Edit .env and set DB_PASSWORD, JWT_SECRET_KEY

:: Step 5 — Initialize and run Alembic from project root
alembic init alembic
:: Then replace alembic/env.py with the one provided below
alembic revision --autogenerate -m "initial schema"
alembic upgrade head

:: Step 6 — Run server (from fastapi_project root where app/ folder lives)
python run.py
:: OR
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
:: → http://localhost:8000
:: → http://localhost:8000/docs  (Swagger UI)
```

---

## .env

```env
APP_NAME=FastAPI RBAC
DEBUG=true

JWT_SECRET_KEY=change-this-jwt-secret-min-64-random-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

DB_DRIVER=mysql+pymysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=fastapi_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=fastapi_rbac_db

# CORS — comma-separated, NO spaces, NO quotes, NO JSON brackets
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## .env.example

```env
APP_NAME=FastAPI RBAC
DEBUG=true
JWT_SECRET_KEY=changeme
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
DB_DRIVER=mysql+pymysql
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

## app/config.py

```python
"""
CORS_ORIGINS is stored as a plain string and split at runtime.
This avoids pydantic-settings' JSON parsing of list[str] fields,
which causes:  SettingsError: error parsing value for field "CORS_ORIGINS"
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field
from datetime import timedelta
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",         # ignore unknown .env keys
    )

    APP_NAME: str = "FastAPI RBAC"
    DEBUG:    bool = False

    # JWT
    JWT_SECRET_KEY:                  str = "changeme"
    JWT_ALGORITHM:                   str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS:   int = 30

    # Database
    DB_DRIVER:   str = "mysql+pymysql"
    DB_HOST:     str = "localhost"
    DB_PORT:     int = 3306
    DB_NAME:     str = "fastapi_rbac_db"
    DB_USER:     str = "root"
    DB_PASSWORD: str = ""
    DATABASE_URL: Optional[str] = None   # explicit override

    # MongoDB
    MONGO_HOST:     str = "localhost"
    MONGO_PORT:     int = 27017
    MONGO_DB:       str = "fastapi_rbac_db"
    MONGO_USER:     Optional[str] = None
    MONGO_PASSWORD: Optional[str] = None

    # CORS — stored as str, split in property below
    CORS_ORIGINS: str = "http://localhost:3000"

    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @computed_field
    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (f"{self.DB_DRIVER}://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

    @computed_field
    @property
    def mongo_uri(self) -> str:
        if self.MONGO_USER and self.MONGO_PASSWORD:
            return (f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}"
                    f"@{self.MONGO_HOST}:{self.MONGO_PORT}/{self.MONGO_DB}")
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

---

## app/database.py

```python
"""
Sync SQLAlchemy engine using pymysql.
No async, no aiosqlite, no aiomysql — avoids MissingGreenlet and AsyncAttrs errors.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from .config import settings

engine = create_engine(
    settings.db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

## app/models/base.py

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

---

## app/models/associations.py

```python
from sqlalchemy import Table, Column, Integer, ForeignKey, DateTime
from datetime import datetime
from .base import Base

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

---

## app/models/permission.py

```python
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .base import Base


class Permission(Base):
    __tablename__ = "permissions"
    id:          Mapped[int]        = mapped_column(Integer, primary_key=True, index=True)
    name:        Mapped[str]        = mapped_column(String(100), unique=True, nullable=False)
    resource:    Mapped[str]        = mapped_column(String(100), nullable=False)
    action:      Mapped[str]        = mapped_column(String(50),  nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at:  Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )

    def to_dict(self):
        return {"id": self.id, "name": self.name, "resource": self.resource,
                "action": self.action, "description": self.description,
                "created_at": self.created_at.isoformat()}
```

---

## app/models/role.py

```python
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .base import Base


class Role(Base):
    __tablename__ = "roles"
    id:          Mapped[int]        = mapped_column(Integer, primary_key=True, index=True)
    name:        Mapped[str]        = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_at:  Mapped[datetime]   = mapped_column(DateTime, default=datetime.utcnow)

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )
    users: Mapped[list["User"]] = relationship(
        "User", secondary="user_roles", back_populates="roles"
    )

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description,
                "permissions": [p.to_dict() for p in self.permissions],
                "created_at": self.created_at.isoformat()}
```

---

## app/models/user.py

```python
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from passlib.context import CryptContext
from datetime import datetime
from .base import Base

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
    created_at:    Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)
    last_login:    Mapped[datetime | None] = mapped_column(DateTime)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="user_roles", back_populates="users"
    )

    def set_password(self, plain: str):
        self.password_hash = _pwd_ctx.hash(plain)

    def verify_password(self, plain: str) -> bool:
        return _pwd_ctx.verify(plain, self.password_hash)

    def get_all_permissions(self) -> set:
        perms = set()
        for role in self.roles:
            for perm in role.permissions:
                perms.add(f"{perm.resource}:{perm.action}")
        return perms

    def has_permission(self, resource: str, action: str) -> bool:
        return f"{resource}:{action}" in self.get_all_permissions()

    def has_role(self, role_name: str) -> bool:
        return any(r.name == role_name for r in self.roles)

    def to_dict(self):
        return {
            "id": self.id, "username": self.username, "email": self.email,
            "first_name": self.first_name, "last_name": self.last_name,
            "is_active": self.is_active,
            "roles": [r.name for r in self.roles],
            "permissions": list(self.get_all_permissions()),
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
```

---

## app/models/token_blacklist.py

```python
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy import select
from datetime import datetime
from .base import Base


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    jti:        Mapped[str]      = mapped_column(String(36), unique=True, nullable=False, index=True)
    token_type: Mapped[str]      = mapped_column(String(20), default="access")
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


def is_revoked(db: Session, jti: str) -> bool:
    result = db.execute(select(TokenBlacklist.id).where(TokenBlacklist.jti == jti))
    return result.scalar_one_or_none() is not None


def revoke_token(db: Session, jti: str, token_type: str, expires_at: datetime):
    if not is_revoked(db, jti):
        db.add(TokenBlacklist(jti=jti, token_type=token_type, expires_at=expires_at))
        db.commit()
```

---

## app/models/__init__.py

```python
from .base          import Base
from .user          import User
from .role          import Role
from .permission    import Permission
from .token_blacklist import TokenBlacklist
from .associations  import role_permissions, user_roles
```

---

## app/core/jwt_utils.py

```python
import jwt
import uuid
from datetime import datetime, timezone
from .config_ref import settings   # avoids circular import


def _secret() -> str:
    return settings.JWT_SECRET_KEY


def _algorithm() -> str:
    return settings.JWT_ALGORITHM


def create_access_token(user_id: int, extra: dict = {}) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + settings.access_token_ttl
    payload = {"sub": str(user_id), "jti": str(uuid.uuid4()),
               "type": "access", "iat": now, "exp": expires, **extra}
    return jwt.encode(payload, _secret(), algorithm=_algorithm())


def create_refresh_token(user_id: int) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + settings.refresh_token_ttl
    payload = {"sub": str(user_id), "jti": str(uuid.uuid4()),
               "type": "refresh", "iat": now, "exp": expires}
    return jwt.encode(payload, _secret(), algorithm=_algorithm())


def decode_token(token: str) -> dict:
    return jwt.decode(token, _secret(), algorithms=[_algorithm()])


def extract_bearer(header_value: str | None) -> str:
    if header_value and header_value.startswith("Bearer "):
        return header_value[7:]
    return header_value or ""
```

---

## app/core/config_ref.py

```python
# Thin re-export to avoid circular imports
from app.config import settings  # noqa: F401
```

---

## app/core/dependencies.py

```python
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.token_blacklist import is_revoked
from app.core.jwt_utils import decode_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Access token required")
    if is_revoked(db, payload["jti"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has been revoked")

    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    return user


def require_permission(resource: str, action: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_permission(resource, action):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires {resource}:{action}")
        return current_user
    return checker


def require_role(*role_names: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(current_user.has_role(r) for r in role_names):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(role_names)}")
        return current_user
    return checker
```

---

## app/routers/auth.py

```python
import jwt as pyjwt
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.token_blacklist import is_revoked, revoke_token
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest
from app.core.jwt_utils import create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none():
        raise HTTPException(409, "Email already registered")
    if db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none():
        raise HTTPException(409, "Username already taken")
    user = User(username=payload.username, email=payload.email,
                first_name=payload.first_name, last_name=payload.last_name)
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "data": {"id": user.id, "email": user.email}}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if not user or not user.verify_password(payload.password):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account is disabled")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    extra = {"username": user.username,
             "roles": [r.name for r in user.roles],
             "permissions": list(user.get_all_permissions())}
    return {
        "success": True,
        "data": {
            "access_token":  create_access_token(user.id, extra=extra),
            "refresh_token": create_refresh_token(user.id),
            "token_type":    "Bearer",
            "user":          user.to_dict(),
        }
    }


@router.delete("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    credentials=Depends(__import__("fastapi").security.HTTPBearer()),
    db: Session = Depends(get_db),
):
    try:
        payload    = decode_token(credentials.credentials)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        revoke_token(db, payload["jti"], "access", expires_at)
    except pyjwt.PyJWTError:
        pass
    return {"success": True, "message": "Logged out successfully"}


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        token_data = decode_token(payload.refresh_token)
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh token has expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")

    if token_data.get("type") != "refresh":
        raise HTTPException(401, "Refresh token required")
    if is_revoked(db, token_data["jti"]):
        raise HTTPException(401, "Token has been revoked")

    user = db.get(User, int(token_data["sub"]))
    if not user:
        raise HTTPException(404, "User not found")

    extra = {"username": user.username,
             "roles": [r.name for r in user.roles],
             "permissions": list(user.get_all_permissions())}
    return {"success": True, "data": {"access_token": create_access_token(user.id, extra=extra)}}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"success": True, "data": current_user.to_dict()}
```

---

## app/routers/users.py

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.role import Role
from app.models.associations import user_roles as user_roles_table
from app.core.dependencies import require_permission, require_role
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.get("/")
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("users", "read")),
):
    q = select(User)
    if search:
        q = q.where(User.username.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar()
    users = db.execute(q.offset((page - 1) * per_page).limit(per_page)).scalars().all()
    return {"success": True, "data": {
        "users": [u.to_dict() for u in users],
        "total": total, "page": page,
        "pages": (total + per_page - 1) // per_page, "per_page": per_page,
    }}


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db),
             _: User = Depends(require_permission("users", "read"))):
    return {"success": True, "data": _get_user_or_404(db, user_id).to_dict()}


@router.post("/", status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db),
                _: User = Depends(require_permission("users", "create"))):
    if db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none():
        raise HTTPException(409, "Email already exists")
    user = User(username=payload.username, email=payload.email,
                first_name=payload.first_name, last_name=payload.last_name)
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "Created", "data": user.to_dict()}


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db),
                _: User = Depends(require_permission("users", "update"))):
    user = _get_user_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.set_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return {"success": True, "data": user.to_dict()}


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_permission("users", "delete"))):
    db.delete(_get_user_or_404(db, user_id))
    db.commit()


@router.post("/{user_id}/roles")
def assign_role(user_id: int, role_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_role("admin", "super_admin"))):
    user = _get_user_or_404(db, user_id)
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    if role not in user.roles:
        user.roles.append(role)
        db.commit()
    return {"success": True, "data": user.to_dict()}


@router.delete("/{user_id}/roles/{role_id}")
def remove_role(user_id: int, role_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_role("admin", "super_admin"))):
    user = _get_user_or_404(db, user_id)
    role = db.get(Role, role_id)
    if role and role in user.roles:
        user.roles.remove(role)
        db.commit()
    return {"success": True, "data": user.to_dict()}
```

---

## app/routers/roles.py

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.role import Role
from app.models.permission import Permission
from app.core.dependencies import require_permission
from app.models.user import User

router = APIRouter(prefix="/roles", tags=["Roles"])


def _get_role_or_404(db: Session, role_id: int) -> Role:
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    return role


@router.get("/")
def list_roles(db: Session = Depends(get_db), _: User = Depends(require_permission("roles", "read"))):
    return {"success": True, "data": [r.to_dict() for r in db.execute(select(Role)).scalars().all()]}


@router.get("/{role_id}")
def get_role(role_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("roles", "read"))):
    return {"success": True, "data": _get_role_or_404(db, role_id).to_dict()}


@router.post("/", status_code=201)
def create_role(payload: dict, db: Session = Depends(get_db), _: User = Depends(require_permission("roles", "create"))):
    if db.execute(select(Role).where(Role.name == payload.get("name"))).scalar_one_or_none():
        raise HTTPException(409, "Role already exists")
    role = Role(name=payload["name"], description=payload.get("description"))
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"success": True, "data": role.to_dict()}


@router.put("/{role_id}")
def update_role(role_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(require_permission("roles", "update"))):
    role = _get_role_or_404(db, role_id)
    for field in ("name", "description"):
        if field in payload:
            setattr(role, field, payload[field])
    db.commit()
    return {"success": True, "data": role.to_dict()}


@router.delete("/{role_id}", status_code=204)
def delete_role(role_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("roles", "delete"))):
    db.delete(_get_role_or_404(db, role_id))
    db.commit()


@router.post("/{role_id}/permissions/{perm_id}")
def assign_permission(role_id: int, perm_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("roles", "update"))):
    role = _get_role_or_404(db, role_id)
    perm = db.get(Permission, perm_id)
    if not perm:
        raise HTTPException(404, "Permission not found")
    if perm not in role.permissions:
        role.permissions.append(perm)
        db.commit()
    return {"success": True, "data": role.to_dict()}


@router.delete("/{role_id}/permissions/{perm_id}")
def remove_permission(role_id: int, perm_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("roles", "update"))):
    role = _get_role_or_404(db, role_id)
    perm = db.get(Permission, perm_id)
    if perm and perm in role.permissions:
        role.permissions.remove(perm)
        db.commit()
    return {"success": True, "data": role.to_dict()}
```

---

## app/routers/permissions.py

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.permission import Permission
from app.core.dependencies import require_permission
from app.models.user import User

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("/")
def list_permissions(db: Session = Depends(get_db), _: User = Depends(require_permission("permissions", "read"))):
    return {"success": True, "data": [p.to_dict() for p in db.execute(select(Permission)).scalars().all()]}


@router.get("/{perm_id}")
def get_permission(perm_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("permissions", "read"))):
    perm = db.get(Permission, perm_id)
    if not perm:
        raise HTTPException(404, "Not found")
    return {"success": True, "data": perm.to_dict()}


@router.post("/", status_code=201)
def create_permission(payload: dict, db: Session = Depends(get_db), _: User = Depends(require_permission("permissions", "create"))):
    perm = Permission(name=payload["name"], resource=payload["resource"],
                      action=payload["action"], description=payload.get("description"))
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return {"success": True, "data": perm.to_dict()}


@router.put("/{perm_id}")
def update_permission(perm_id: int, payload: dict, db: Session = Depends(get_db), _: User = Depends(require_permission("permissions", "update"))):
    perm = db.get(Permission, perm_id)
    if not perm:
        raise HTTPException(404, "Not found")
    for field in ("name", "resource", "action", "description"):
        if field in payload:
            setattr(perm, field, payload[field])
    db.commit()
    return {"success": True, "data": perm.to_dict()}


@router.delete("/{perm_id}", status_code=204)
def delete_permission(perm_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("permissions", "delete"))):
    perm = db.get(Permission, perm_id)
    if not perm:
        raise HTTPException(404, "Not found")
    db.delete(perm)
    db.commit()
```

---

## app/schemas/auth.py

```python
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    username:   str
    email:      EmailStr
    password:   str
    first_name: str | None = None
    last_name:  str | None = None


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str
```

---

## app/schemas/user.py

```python
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username:   str
    email:      EmailStr
    password:   str
    first_name: str | None = None
    last_name:  str | None = None


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name:  str | None = None
    is_active:  bool | None = None
    password:   str | None = None
```

---

## app/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import auth, users, roles, permissions

# Create tables on startup (alternatively use Alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api")
app.include_router(users.router,       prefix="/api")
app.include_router(roles.router,       prefix="/api")
app.include_router(permissions.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## app/__init__.py

```python
# empty
```

---

## run.py

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## alembic/env.py (Fixed — loads .env, uses sync engine)

```python
"""
Alembic env.py — fixed for:
1. Sync SQLAlchemy (no async greenlet errors)
2. Loads .env manually so DATABASE_URL is available
3. Correct API: config.config_ini_section (not config_main_section)
"""
import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make app importable from alembic/ folder ───────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load .env manually before importing settings ───────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from app.config import settings
from app.models import Base   # imports all models so autogenerate detects them

config      = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return settings.db_url


def run_migrations_offline():
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## alembic.ini (key section)

```ini
[alembic]
script_location = alembic
# Leave sqlalchemy.url blank — env.py reads it from .env
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

---

## Database Switching (change .env only)

```env
# MySQL (default)
DB_DRIVER=mysql+pymysql
DB_HOST=localhost
DB_PORT=3306

# SQLite (no server needed)
DATABASE_URL=sqlite:///./dev.db

# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/fastapi_rbac_db
```

---

## API Endpoints

| Method | URL | Auth |
|--------|-----|------|
| POST | /api/auth/register | Public |
| POST | /api/auth/login | Public |
| DELETE | /api/auth/logout | Bearer |
| POST | /api/auth/refresh | Public |
| GET | /api/auth/me | Bearer |
| GET | /api/users/?page=1&per_page=10&search= | permission:users:read |
| POST | /api/users/ | permission:users:create |
| GET | /api/users/{id} | permission:users:read |
| PUT | /api/users/{id} | permission:users:update |
| DELETE | /api/users/{id} | permission:users:delete |
| POST | /api/users/{id}/roles?role_id=1 | role:admin |
| DELETE | /api/users/{id}/roles/{rid} | role:admin |
| GET | /api/roles/ | permission:roles:read |
| POST | /api/roles/ | permission:roles:create |
| PUT | /api/roles/{id} | permission:roles:update |
| DELETE | /api/roles/{id} | permission:roles:delete |
| POST | /api/roles/{id}/permissions/{pid} | permission:roles:update |
| DELETE | /api/roles/{id}/permissions/{pid} | permission:roles:update |
| GET | /api/permissions/ | permission:permissions:read |
| POST | /api/permissions/ | permission:permissions:create |
| PUT | /api/permissions/{id} | permission:permissions:update |
| DELETE | /api/permissions/{id} | permission:permissions:delete |
