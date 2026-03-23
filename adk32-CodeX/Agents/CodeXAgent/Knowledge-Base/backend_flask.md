# Flask Backend Architecture — Real-World Production Guide

> Complete REST API using **PyJWT** (manual JWT — no SimpleJWT), **MySQL as default database**, all credentials via `.env`, Dynamic RBAC, and full CRUD integration.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Environment Setup](#environment-setup)
4. [Database Configuration](#database-configuration)
5. [Models & Schema Design](#models--schema-design)
6. [JWT Implementation (PyJWT)](#jwt-implementation-pyjwt)
7. [Auth Middleware Decorators](#auth-middleware-decorators)
8. [Authentication Routes](#authentication-routes)
9. [CRUD Routes & Services](#crud-routes--services)
10. [MongoDB Integration](#mongodb-integration)
11. [Database Switching Guide](#database-switching-guide)
12. [API Endpoint Summary](#api-endpoint-summary)

---

## Project Overview

This guide builds a production-ready REST API using **Flask** with:

- **PyJWT** for manual JWT creation, verification, and DB-backed blacklist (no flask-jwt-extended / SimpleJWT)
- **MySQL** as the default database (switchable via `.env` only — no code changes)
- All secrets and DB credentials loaded exclusively from `.env`
- Dynamic Role-Based Access Control: Permission → Role → RolePermission → UserRole
- Full CRUD for Users, Roles, and Permissions

---

## Project Structure

```
flask_project/
├── app/
│   ├── __init__.py               # App factory
│   ├── config.py                 # .env-driven configuration
│   ├── extensions.py             # SQLAlchemy, Bcrypt, CORS
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   ├── associations.py       # Many-to-many join tables
│   │   └── token_blacklist.py    # DB-backed JWT revocation
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py
│   │   ├── user_routes.py
│   │   ├── role_routes.py
│   │   └── permission_routes.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── role_service.py
│   │   └── permission_service.py
│   │
│   ├── middleware/
│   │   └── auth_middleware.py    # jwt_required, permission_required, role_required
│   │
│   ├── mongo_models/
│   │   └── user_activity.py
│   │
│   └── utils/
│       ├── jwt_utils.py          # create / decode token helpers
│       └── response.py
│
├── migrations/
├── tests/
├── .env                          # ← ALL secrets live here
├── .env.example
├── requirements.txt
├── run.py
├── wsgi.py
└── README.md   # Complete information about setup and execution.
```

---

## Environment Setup

### requirements.txt

```txt
flask==3.0.3
flask-sqlalchemy==3.1.1
flask-migrate==4.0.7
flask-bcrypt==1.0.1
flask-cors==4.0.1
PyJWT==2.8.0
python-dotenv==1.0.1
python-decouple==3.8

# MySQL driver (default)
PyMySQL==1.1.1
cryptography==42.0.8

# Optional — other SQL drivers
psycopg2-binary==2.9.9    # PostgreSQL
# mysqlclient==2.2.4       # alternative MySQL C driver

# MongoDB
mongoengine==0.28.2

# Production
gunicorn==22.0.0
```

### .env

```env
# ─── Flask ─────────────────────────────────────────────────────────────────
FLASK_ENV=development
SECRET_KEY=change-this-flask-secret-key-min-64-chars-random

# ─── JWT (PyJWT) ────────────────────────────────────────────────────────────
JWT_SECRET_KEY=change-this-jwt-secret-min-64-random-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=3600         # seconds (1 hour)
JWT_REFRESH_TOKEN_EXPIRES=2592000     # seconds (30 days)

# ─── MySQL (Default Database) ────────────────────────────────────────────────
DB_DRIVER=mysql+pymysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flask_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# ─── Override entire URL (optional — SQLite or PostgreSQL) ───────────────────
# DATABASE_URL=sqlite:///dev.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/flask_rbac_db

# ─── MongoDB ─────────────────────────────────────────────────────────────────
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=flask_rbac_db
# MONGO_USER=mongouser
# MONGO_PASSWORD=mongopassword

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### .env.example

```env
FLASK_ENV=development
SECRET_KEY=changeme
JWT_SECRET_KEY=changeme
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
DB_DRIVER=mysql+pymysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flask_rbac_db
DB_USER=root
DB_PASSWORD=
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=flask_rbac_db
CORS_ORIGINS=http://localhost:3000
```

---

## Database Configuration

### app/config.py

```python
import os
from datetime import timedelta
from decouple import config


def _build_db_url() -> str:
    """
    Construct DATABASE_URL from individual .env variables.
    Falls back to DATABASE_URL if explicitly set.
    Default: MySQL via PyMySQL.
    """
    explicit = config("DATABASE_URL", default=None)
    if explicit:
        return explicit

    driver   = config("DB_DRIVER",   default="mysql+pymysql")
    host     = config("DB_HOST",     default="localhost")
    port     = config("DB_PORT",     default="3306")
    name     = config("DB_NAME",     default="flask_rbac_db")
    user     = config("DB_USER",     default="root")
    password = config("DB_PASSWORD", default="")
    return f"{driver}://{user}:{password}@{host}:{port}/{name}"


def _build_mongo_uri() -> str:
    host     = config("MONGO_HOST",     default="localhost")
    port     = config("MONGO_PORT",     default="27017")
    db       = config("MONGO_DB",       default="flask_rbac_db")
    user     = config("MONGO_USER",     default=None)
    password = config("MONGO_PASSWORD", default=None)
    if user and password:
        return f"mongodb://{user}:{password}@{host}:{port}/{db}"
    return f"mongodb://{host}:{port}/{db}"


class Config:
    # ── Flask core ──────────────────────────────────────────────────────────
    SECRET_KEY = config("SECRET_KEY")
    DEBUG      = False
    TESTING    = False

    # ── JWT — all values from .env ──────────────────────────────────────────
    JWT_SECRET_KEY  = config("JWT_SECRET_KEY")
    JWT_ALGORITHM   = config("JWT_ALGORITHM",              default="HS256")
    JWT_ACCESS_TTL  = timedelta(seconds=config("JWT_ACCESS_TOKEN_EXPIRES",  cast=int, default=3600))
    JWT_REFRESH_TTL = timedelta(seconds=config("JWT_REFRESH_TOKEN_EXPIRES", cast=int, default=2592000))

    # ── SQLAlchemy ──────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI        = _build_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE           = 10
    SQLALCHEMY_POOL_RECYCLE        = 280    # prevent MySQL "server gone away"
    SQLALCHEMY_POOL_PRE_PING       = True

    # ── MongoDB ─────────────────────────────────────────────────────────────
    MONGO_URI = _build_mongo_uri()

    # ── CORS ────────────────────────────────────────────────────────────────
    CORS_ORIGINS = config("CORS_ORIGINS", default="http://localhost:3000").split(",")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    MONGO_URI               = "mongomock://localhost/test"


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}
```

### app/extensions.py

```python
from flask_sqlalchemy import SQLAlchemy
from flask_migrate    import Migrate
from flask_bcrypt     import Bcrypt
from flask_cors       import CORS

db      = SQLAlchemy()
migrate = Migrate()
bcrypt  = Bcrypt()
cors    = CORS()
```

### app/__init__.py

```python
import os
from flask import Flask
import mongoengine

from .config     import config_map
from .extensions import db, migrate, bcrypt, cors


def create_app(env: str = None) -> Flask:
    app = Flask(__name__)

    env = env or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_map[env])

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    # MongoDB
    mongoengine.connect(host=app.config["MONGO_URI"])

    # Blueprints
    from .routes.auth_routes       import auth_bp
    from .routes.user_routes       import user_bp
    from .routes.role_routes       import role_bp
    from .routes.permission_routes import permission_bp

    app.register_blueprint(auth_bp,       url_prefix="/api/auth")
    app.register_blueprint(user_bp,       url_prefix="/api/users")
    app.register_blueprint(role_bp,       url_prefix="/api/roles")
    app.register_blueprint(permission_bp, url_prefix="/api/permissions")

    from .utils.response import register_error_handlers
    register_error_handlers(app)

    return app
```

---

## Models & Schema Design

### app/models/associations.py

```python
from ..extensions import db
from datetime import datetime

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id",       db.Integer, db.ForeignKey("roles.id",       ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    db.Column("granted_at",    db.DateTime, default=datetime.utcnow),
)

user_roles = db.Table(
    "user_roles",
    db.Column("user_id",     db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("role_id",     db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow),
)
```

### app/models/permission.py

```python
from ..extensions import db
from datetime import datetime


class Permission(db.Model):
    __tablename__ = "permissions"

    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(100), unique=True,  nullable=False)
    resource    = db.Column(db.String(100), nullable=False)   # users | roles | posts …
    action      = db.Column(db.String(50),  nullable=False)   # create | read | update | delete
    description = db.Column(db.String(255))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    roles = db.relationship("Role", secondary="role_permissions", back_populates="permissions")

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "resource":    self.resource,
            "action":      self.action,
            "description": self.description,
            "created_at":  self.created_at.isoformat(),
        }
```

### app/models/role.py

```python
from ..extensions import db
from datetime import datetime


class Role(db.Model):
    __tablename__ = "roles"

    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    permissions = db.relationship("Permission", secondary="role_permissions", back_populates="roles")
    users       = db.relationship("User",       secondary="user_roles",       back_populates="roles")

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "permissions": [p.to_dict() for p in self.permissions],
            "created_at":  self.created_at.isoformat(),
        }
```

### app/models/user.py

```python
from ..extensions import db, bcrypt
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer,     primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name    = db.Column(db.String(80))
    last_name     = db.Column(db.String(80))
    is_active     = db.Column(db.Boolean, default=True)
    is_verified   = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login    = db.Column(db.DateTime)

    roles = db.relationship("Role", secondary="user_roles", back_populates="users")

    @property
    def password(self):
        raise AttributeError("Password is write-only")

    @password.setter
    def password(self, plain: str):
        self.password_hash = bcrypt.generate_password_hash(plain).decode("utf-8")

    def verify_password(self, plain: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, plain)

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
            "id":          self.id,
            "username":    self.username,
            "email":       self.email,
            "first_name":  self.first_name,
            "last_name":   self.last_name,
            "is_active":   self.is_active,
            "is_verified": self.is_verified,
            "roles":       [r.name for r in self.roles],
            "permissions": list(self.get_all_permissions()),
            "created_at":  self.created_at.isoformat(),
            "last_login":  self.last_login.isoformat() if self.last_login else None,
        }
```

### app/models/token_blacklist.py

```python
from ..extensions import db
from datetime import datetime


class TokenBlacklist(db.Model):
    """
    DB-backed JWT revocation table.
    Survives server restarts unlike an in-memory set.
    """
    __tablename__ = "token_blacklist"

    id         = db.Column(db.Integer,    primary_key=True)
    jti        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    token_type = db.Column(db.String(20), default="access")   # access | refresh
    revoked_at = db.Column(db.DateTime,   default=datetime.utcnow)
    expires_at = db.Column(db.DateTime,   nullable=False)

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        return db.session.query(cls.id).filter_by(jti=jti).first() is not None

    @classmethod
    def revoke(cls, jti: str, token_type: str, expires_at: datetime):
        if not cls.is_revoked(jti):
            record = cls(jti=jti, token_type=token_type, expires_at=expires_at)
            db.session.add(record)
            db.session.commit()
```

---

## JWT Implementation (PyJWT)

### app/utils/jwt_utils.py

```python
"""
All JWT operations use PyJWT directly — no flask-jwt-extended or SimpleJWT.
Secret and algorithm are read from Flask app.config (sourced from .env).
"""

import jwt
import uuid
from datetime import datetime, timezone
from flask import current_app
from typing import Optional


def _secret() -> str:
    return current_app.config["JWT_SECRET_KEY"]


def _algorithm() -> str:
    return current_app.config["JWT_ALGORITHM"]


def create_access_token(user_id: int, extra: dict = {}) -> str:
    """
    Build and sign an access token.

    Payload fields:
      sub   — user ID (string)
      jti   — unique token ID (used for blacklist lookup)
      type  — "access"
      iat   — issued at
      exp   — expiry timestamp
      + any extra claims (roles, permissions, username …)
    """
    now     = datetime.now(timezone.utc)
    expires = now + current_app.config["JWT_ACCESS_TTL"]

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
    """Build and sign a refresh token (minimal payload — no permission claims)."""
    now     = datetime.now(timezone.utc)
    expires = now + current_app.config["JWT_REFRESH_TTL"]

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
    Decode and verify signature + expiry.
    Raises:
      jwt.ExpiredSignatureError  — token past expiry
      jwt.InvalidTokenError      — bad signature / malformed
    """
    return jwt.decode(token, _secret(), algorithms=[_algorithm()])


def extract_bearer(header_value: str) -> str:
    """Strip 'Bearer ' prefix from Authorization header value."""
    if header_value and header_value.startswith("Bearer "):
        return header_value[7:]
    return header_value or ""
```

---

## Auth Middleware Decorators

### app/middleware/auth_middleware.py

```python
"""
PyJWT-based Flask middleware — mirrors the decorator pattern in the project spec.

Usage:
    @jwt_required
    def my_view():
        user = g.current_user
        ...

    @permission_required("users", "delete")
    def delete_user(user_id): ...

    @role_required("admin", "super_admin")
    def admin_only(): ...
"""

import jwt as pyjwt
from functools import wraps
from flask import request, jsonify, g

from ..models.user            import User
from ..models.token_blacklist  import TokenBlacklist
from ..utils.jwt_utils        import decode_token, extract_bearer


# ─────────────────────────────────────────────────────────────────────────────
# Core: jwt_required
# ─────────────────────────────────────────────────────────────────────────────

def jwt_required(func):
    """
    Verify the Bearer JWT on every decorated request.
    Attaches the authenticated User to flask.g.current_user.
    Also attaches the decoded payload to flask.g.token_payload.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token       = extract_bearer(auth_header)

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        # ── Decode & verify signature / expiry ───────────────────────────────
        try:
            payload = decode_token(token)
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        # ── Ensure this is an access token ───────────────────────────────────
        if payload.get("type") != "access":
            return jsonify({"error": "Access token required"}), 401

        # ── Check DB-backed blacklist (survives restarts) ────────────────────
        if TokenBlacklist.is_revoked(payload["jti"]):
            return jsonify({"error": "Token has been revoked"}), 401

        # ── Load user from DB ────────────────────────────────────────────────
        try:
            user = User.query.get(int(payload["sub"]))
        except (ValueError, Exception):
            return jsonify({"error": "Invalid token subject"}), 401

        if not user:
            return jsonify({"error": "User not found"}), 401
        if not user.is_active:
            return jsonify({"error": "Account is disabled"}), 403

        # ── Attach to request context ────────────────────────────────────────
        g.current_user  = user
        g.token_payload = payload

        return func(*args, **kwargs)

    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# RBAC: permission_required
# ─────────────────────────────────────────────────────────────────────────────

def permission_required(resource: str, action: str):
    """
    Decorator factory: check that the authenticated user has resource:action.
    Internally applies @jwt_required first.
    """
    def decorator(func):
        @wraps(func)
        @jwt_required
        def wrapper(*args, **kwargs):
            user: User = g.current_user
            if not user.has_permission(resource, action):
                return jsonify({
                    "error":    "Forbidden",
                    "required": f"{resource}:{action}",
                }), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# RBAC: role_required
# ─────────────────────────────────────────────────────────────────────────────

def role_required(*role_names: str):
    """
    Decorator factory: check that the authenticated user has one of the roles.
    Internally applies @jwt_required first.
    """
    def decorator(func):
        @wraps(func)
        @jwt_required
        def wrapper(*args, **kwargs):
            user: User = g.current_user
            if not any(user.has_role(r) for r in role_names):
                return jsonify({
                    "error":          "Forbidden",
                    "required_roles": list(role_names),
                }), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## Authentication Routes

### app/services/auth_service.py

```python
import jwt as pyjwt
from datetime import datetime, timezone

from ..models.user            import User
from ..models.token_blacklist  import TokenBlacklist
from ..extensions             import db
from ..utils.jwt_utils        import create_access_token, create_refresh_token, decode_token, extract_bearer
from ..utils.response         import ApiError


class AuthService:

    @staticmethod
    def register(data: dict) -> User:
        if User.query.filter_by(email=data["email"]).first():
            raise ApiError("Email already registered", 409)
        if User.query.filter_by(username=data["username"]).first():
            raise ApiError("Username already taken", 409)

        user           = User(
            username   = data["username"],
            email      = data["email"],
            first_name = data.get("first_name"),
            last_name  = data.get("last_name"),
        )
        user.password  = data["password"]   # triggers bcrypt setter
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def login(email: str, password: str) -> dict:
        user = User.query.filter_by(email=email).first()
        if not user or not user.verify_password(password):
            raise ApiError("Invalid credentials", 401)
        if not user.is_active:
            raise ApiError("Account is disabled", 403)

        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        extra = {
            "username":    user.username,
            "roles":       [r.name for r in user.roles],
            "permissions": list(user.get_all_permissions()),
        }
        access_token  = create_access_token(user.id, extra=extra)
        refresh_token = create_refresh_token(user.id)

        return {
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "token_type":    "Bearer",
            "user":          user.to_dict(),
        }

    @staticmethod
    def logout(auth_header: str) -> dict:
        token = extract_bearer(auth_header)
        try:
            payload  = decode_token(token)
            jti      = payload["jti"]
            exp      = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            TokenBlacklist.revoke(jti=jti, token_type="access", expires_at=exp)
        except pyjwt.PyJWTError:
            pass    # already invalid — still succeed
        return {"message": "Logged out successfully"}

    @staticmethod
    def refresh(refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except pyjwt.ExpiredSignatureError:
            raise ApiError("Refresh token has expired", 401)
        except pyjwt.InvalidTokenError:
            raise ApiError("Invalid refresh token", 401)

        if payload.get("type") != "refresh":
            raise ApiError("Refresh token required", 401)
        if TokenBlacklist.is_revoked(payload["jti"]):
            raise ApiError("Refresh token has been revoked", 401)

        user = User.query.get(int(payload["sub"]))
        if not user:
            raise ApiError("User not found", 404)

        extra = {
            "username":    user.username,
            "roles":       [r.name for r in user.roles],
            "permissions": list(user.get_all_permissions()),
        }
        return {"access_token": create_access_token(user.id, extra=extra), "token_type": "Bearer"}
```

### app/routes/auth_routes.py

```python
from flask import Blueprint, request, g
from ..services.auth_service import AuthService
from ..middleware.auth_middleware import jwt_required
from ..utils.response import success_response, error_response

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data    = request.get_json() or {}
    missing = [f for f in ("username", "email", "password") if not data.get(f)]
    if missing:
        return error_response(f"Missing: {', '.join(missing)}", 400)
    user = AuthService.register(data)
    return success_response(user.to_dict(), "Registered successfully", 201)


@auth_bp.route("/login", methods=["POST"])
def login():
    data   = request.get_json() or {}
    result = AuthService.login(data.get("email", ""), data.get("password", ""))
    return success_response(result, "Login successful")


@auth_bp.route("/logout", methods=["DELETE"])
@jwt_required
def logout():
    result = AuthService.logout(request.headers.get("Authorization", ""))
    return success_response(result)


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data   = request.get_json() or {}
    result = AuthService.refresh(data.get("refresh_token", ""))
    return success_response(result, "Token refreshed")


@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me():
    return success_response(g.current_user.to_dict())
```

---

## CRUD Routes & Services

### app/routes/user_routes.py

```python
from flask import Blueprint, request, g
from ..services.user_service import UserService
from ..middleware.auth_middleware import permission_required, role_required
from ..utils.response import success_response

user_bp = Blueprint("users", __name__)


@user_bp.route("/", methods=["GET"])
@permission_required("users", "read")
def list_users():
    result = UserService.get_all(
        page     = request.args.get("page",     1,  type=int),
        per_page = request.args.get("per_page", 10, type=int),
        search   = request.args.get("search",   ""),
    )
    return success_response(result)


@user_bp.route("/<int:user_id>", methods=["GET"])
@permission_required("users", "read")
def get_user(user_id):
    return success_response(UserService.get_by_id(user_id).to_dict())


@user_bp.route("/", methods=["POST"])
@permission_required("users", "create")
def create_user():
    return success_response(UserService.create(request.get_json() or {}).to_dict(), "User created", 201)


@user_bp.route("/<int:user_id>", methods=["PUT"])
@permission_required("users", "update")
def update_user(user_id):
    return success_response(UserService.update(user_id, request.get_json() or {}).to_dict(), "User updated")


@user_bp.route("/<int:user_id>", methods=["DELETE"])
@permission_required("users", "delete")
def delete_user(user_id):
    UserService.delete(user_id)
    return success_response(None, "User deleted")


@user_bp.route("/<int:user_id>/roles", methods=["POST"])
@role_required("admin", "super_admin")
def assign_role(user_id):
    data = request.get_json() or {}
    return success_response(UserService.assign_role(user_id, data.get("role_id")).to_dict(), "Role assigned")


@user_bp.route("/<int:user_id>/roles/<int:role_id>", methods=["DELETE"])
@role_required("admin", "super_admin")
def remove_role(user_id, role_id):
    return success_response(UserService.remove_role(user_id, role_id).to_dict(), "Role removed")
```

### app/routes/role_routes.py

```python
from flask import Blueprint, request
from ..services.role_service import RoleService
from ..middleware.auth_middleware import permission_required
from ..utils.response import success_response

role_bp = Blueprint("roles", __name__)


@role_bp.route("/", methods=["GET"])
@permission_required("roles", "read")
def list_roles():
    return success_response([r.to_dict() for r in RoleService.get_all()])


@role_bp.route("/<int:role_id>", methods=["GET"])
@permission_required("roles", "read")
def get_role(role_id):
    return success_response(RoleService.get_by_id(role_id).to_dict())


@role_bp.route("/", methods=["POST"])
@permission_required("roles", "create")
def create_role():
    return success_response(RoleService.create(request.get_json() or {}).to_dict(), "Role created", 201)


@role_bp.route("/<int:role_id>", methods=["PUT"])
@permission_required("roles", "update")
def update_role(role_id):
    return success_response(RoleService.update(role_id, request.get_json() or {}).to_dict(), "Role updated")


@role_bp.route("/<int:role_id>", methods=["DELETE"])
@permission_required("roles", "delete")
def delete_role(role_id):
    RoleService.delete(role_id)
    return success_response(None, "Role deleted")


@role_bp.route("/<int:role_id>/permissions", methods=["POST"])
@permission_required("roles", "update")
def assign_permission(role_id):
    data = request.get_json() or {}
    return success_response(RoleService.assign_permission(role_id, data.get("permission_id")).to_dict(), "Permission assigned")


@role_bp.route("/<int:role_id>/permissions/<int:perm_id>", methods=["DELETE"])
@permission_required("roles", "update")
def remove_permission(role_id, perm_id):
    return success_response(RoleService.remove_permission(role_id, perm_id).to_dict(), "Permission removed")
```

### app/services/user_service.py

```python
from ..models.user import User
from ..models.role import Role
from ..extensions  import db
from ..utils.response import ApiError


class UserService:

    @staticmethod
    def get_all(page=1, per_page=10, search=""):
        q = User.query
        if search:
            q = q.filter(
                User.username.ilike(f"%{search}%") |
                User.email.ilike(f"%{search}%")
            )
        pag = q.paginate(page=page, per_page=per_page, error_out=False)
        return {
            "users":    [u.to_dict() for u in pag.items],
            "total":    pag.total,
            "page":     pag.page,
            "pages":    pag.pages,
            "per_page": per_page,
        }

    @staticmethod
    def get_by_id(user_id: int) -> User:
        user = User.query.get(user_id)
        if not user:
            raise ApiError("User not found", 404)
        return user

    @staticmethod
    def create(data: dict) -> User:
        if User.query.filter_by(email=data.get("email")).first():
            raise ApiError("Email already exists", 409)
        user = User(username=data["username"], email=data["email"],
                    first_name=data.get("first_name"), last_name=data.get("last_name"))
        user.password = data["password"]
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update(user_id: int, data: dict) -> User:
        user = UserService.get_by_id(user_id)
        for field in ("first_name", "last_name", "is_active"):
            if field in data:
                setattr(user, field, data[field])
        if data.get("password"):
            user.password = data["password"]
        db.session.commit()
        return user

    @staticmethod
    def delete(user_id: int):
        user = UserService.get_by_id(user_id)
        db.session.delete(user)
        db.session.commit()

    @staticmethod
    def assign_role(user_id: int, role_id: int) -> User:
        user = UserService.get_by_id(user_id)
        role = Role.query.get(role_id)
        if not role:
            raise ApiError("Role not found", 404)
        if role not in user.roles:
            user.roles.append(role)
            db.session.commit()
        return user

    @staticmethod
    def remove_role(user_id: int, role_id: int) -> User:
        user = UserService.get_by_id(user_id)
        role = Role.query.get(role_id)
        if role and role in user.roles:
            user.roles.remove(role)
            db.session.commit()
        return user
```

### app/services/role_service.py

```python
from ..models.role       import Role
from ..models.permission import Permission
from ..extensions        import db
from ..utils.response    import ApiError


class RoleService:

    @staticmethod
    def get_all():
        return Role.query.all()

    @staticmethod
    def get_by_id(role_id: int) -> Role:
        role = Role.query.get(role_id)
        if not role:
            raise ApiError("Role not found", 404)
        return role

    @staticmethod
    def create(data: dict) -> Role:
        if Role.query.filter_by(name=data.get("name")).first():
            raise ApiError("Role already exists", 409)
        role = Role(name=data["name"], description=data.get("description"))
        db.session.add(role)
        db.session.commit()
        return role

    @staticmethod
    def update(role_id: int, data: dict) -> Role:
        role = RoleService.get_by_id(role_id)
        for field in ("name", "description"):
            if field in data:
                setattr(role, field, data[field])
        db.session.commit()
        return role

    @staticmethod
    def delete(role_id: int):
        role = RoleService.get_by_id(role_id)
        db.session.delete(role)
        db.session.commit()

    @staticmethod
    def assign_permission(role_id: int, perm_id: int) -> Role:
        role = RoleService.get_by_id(role_id)
        perm = Permission.query.get(perm_id)
        if not perm:
            raise ApiError("Permission not found", 404)
        if perm not in role.permissions:
            role.permissions.append(perm)
            db.session.commit()
        return role

    @staticmethod
    def remove_permission(role_id: int, perm_id: int) -> Role:
        role = RoleService.get_by_id(role_id)
        perm = Permission.query.get(perm_id)
        if perm and perm in role.permissions:
            role.permissions.remove(perm)
            db.session.commit()
        return role
```

---

## Error Handling

### app/utils/response.py

```python
from flask import jsonify


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message     = message
        self.status_code = status_code


def success_response(data=None, message="Success", status_code=200):
    body = {"success": True, "message": message}
    if data is not None:
        body["data"] = data
    return jsonify(body), status_code


def error_response(message="Error", status_code=400, errors=None):
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(e):
        return error_response(e.message, e.status_code)

    @app.errorhandler(404)
    def not_found(_):
        return error_response("Resource not found", 404)

    @app.errorhandler(405)
    def method_not_allowed(_):
        return error_response("Method not allowed", 405)

    @app.errorhandler(500)
    def internal_error(_):
        return error_response("Internal server error", 500)
```

---

## MongoDB Integration

### app/mongo_models/user_activity.py

```python
from mongoengine import Document, StringField, DateTimeField, DictField
from datetime import datetime


class UserActivity(Document):
    """Flexible audit log stored in MongoDB."""
    user_id    = StringField(required=True)
    action     = StringField(required=True)   # login | logout | create_user …
    resource   = StringField()
    metadata   = DictField()
    ip_address = StringField()
    user_agent = StringField()
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "user_activities",
        "indexes":    ["user_id", "action", "-created_at"],
        "ordering":   ["-created_at"],
    }
```

---

## Database Switching Guide

Only `.env` changes are needed — all models and services remain identical.

```env
# ── MySQL (default) ──────────────────────────────────────────────────────────
DB_DRIVER=mysql+pymysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flask_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# ── SQLite (development only — set DATABASE_URL to override) ─────────────────
DATABASE_URL=sqlite:///dev.db

# ── PostgreSQL (production alternative) ──────────────────────────────────────
DATABASE_URL=postgresql://user:pass@localhost:5432/flask_rbac_db
```

```bash
# MySQL: create the database first
mysql -u root -p -e "CREATE DATABASE flask_rbac_db CHARACTER SET utf8mb4;"

# Run migrations
flask db init
flask db migrate -m "initial schema"
flask db upgrade
```

---

## run.py

```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

---

## API Endpoint Summary

| Method | Endpoint | Description | Guard |
|--------|----------|-------------|-------|
| POST | /api/auth/register | Register | Public |
| POST | /api/auth/login | Login → JWT tokens | Public |
| DELETE | /api/auth/logout | Revoke access token | jwt_required |
| POST | /api/auth/refresh | New access token | Public |
| GET | /api/auth/me | Current user info | jwt_required |
| GET | /api/users/ | List users (paginated) | permission: users:read |
| POST | /api/users/ | Create user | permission: users:create |
| GET | /api/users/\<id\> | Get user by ID | permission: users:read |
| PUT | /api/users/\<id\> | Update user | permission: users:update |
| DELETE | /api/users/\<id\> | Delete user | permission: users:delete |
| POST | /api/users/\<id\>/roles | Assign role to user | role: admin |
| DELETE | /api/users/\<id\>/roles/\<rid\> | Remove role from user | role: admin |
| GET | /api/roles/ | List roles | permission: roles:read |
| POST | /api/roles/ | Create role | permission: roles:create |
| GET | /api/roles/\<id\> | Get role | permission: roles:read |
| PUT | /api/roles/\<id\> | Update role | permission: roles:update |
| DELETE | /api/roles/\<id\> | Delete role | permission: roles:delete |
| POST | /api/roles/\<id\>/permissions | Assign permission to role | permission: roles:update |
| DELETE | /api/roles/\<id\>/permissions/\<pid\> | Remove permission | permission: roles:update |
| GET | /api/permissions/ | List permissions | permission: permissions:read |
| POST | /api/permissions/ | Create permission | permission: permissions:create |
| PUT | /api/permissions/\<id\> | Update permission | permission: permissions:update |
| DELETE | /api/permissions/\<id\> | Delete permission | permission: permissions:delete |
