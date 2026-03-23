# Django Backend Architecture — Real-World Production Guide

> Complete REST API using **PyJWT** (manual JWT — no SimpleJWT), **MySQL as default database**, all credentials from `.env`, Custom RBAC, and full CRUD via Django REST Framework.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Environment Setup](#environment-setup)
4. [Settings Configuration](#settings-configuration)
5. [Models & Schema Design](#models--schema-design)
6. [JWT Implementation (PyJWT)](#jwt-implementation-pyjwt)
7. [Auth Middleware Decorator](#auth-middleware-decorator)
8. [Authentication Views](#authentication-views)
9. [DRF Permission Classes](#drf-permission-classes)
10. [CRUD ViewSets](#crud-viewsets)
11. [MongoDB Integration](#mongodb-integration)
12. [Management Command — Seed RBAC](#management-command--seed-rbac)
13. [API Endpoint Summary](#api-endpoint-summary)

---

## Project Overview

- **PyJWT** (manual) — decorator pattern exactly matching the provided project spec
- **MySQL** as default (one `.env` change to switch to SQLite/PostgreSQL)
- Custom `TokenBlacklist` model in DB (survives restarts)
- Dynamic RBAC: Permission → Role → RolePermission → UserRole
- Full CRUD via DRF ViewSets

---

## Project Structure

```
django_project/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── authentication/
│   │   ├── models.py        # TokenBlacklist
│   │   ├── jwt_utils.py     # PyJWT helpers
│   │   ├── middleware.py    # jwt_required decorator (matches spec)
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── users/
│   │   ├── models.py        # Custom User
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   │
│   ├── rbac/
│   │   ├── models.py        # Permission, Role, RolePermission, UserRole
│   │   ├── permissions.py   # DRF permission classes
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── management/commands/seed_rbac.py
│   │
│   └── activity/
│       └── mongo_models.py
│
├── core/
│   ├── pagination.py
│   └── exceptions.py
│
├── requirements/
│   ├── base.txt
│   └── development.txt
├── manage.py
├── .env
├── .env.example
└── README.md   # Complete information about setup and execution.
```

---

## Environment Setup

### requirements/base.txt

```txt
Django==5.0.7
djangorestframework==3.15.2
django-cors-headers==4.4.0
django-environ==0.11.2
django-filter==24.3
PyJWT==2.8.0
mysqlclient==2.2.4           # MySQL (default)
mongoengine==0.28.2
gunicorn==22.0.0
whitenoise==6.7.0
psycopg2-binary==2.9.9       # optional — PostgreSQL
```

### .env

```env
# ─── Django ──────────────────────────────────────────────────────────────────
DJANGO_ENV=development
SECRET_KEY=change-this-django-secret-min-50-random-chars

# ─── JWT (PyJWT) ─────────────────────────────────────────────────────────────
JWT_SECRET_KEY=change-this-jwt-secret-min-64-random-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_SECONDS=3600       # 1 hour
JWT_REFRESH_TOKEN_EXPIRE_SECONDS=2592000   # 30 days

# ─── MySQL (Default Database) ────────────────────────────────────────────────
DB_ENGINE=django.db.backends.mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=django_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# ─── Switch to SQLite (set DB_ENGINE + DB_NAME) ───────────────────────────
# DB_ENGINE=django.db.backends.sqlite3
# DB_NAME=db.sqlite3

# ─── Switch to PostgreSQL ─────────────────────────────────────────────────
# DB_ENGINE=django.db.backends.postgresql
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=django_rbac_db
# DB_USER=postgres
# DB_PASSWORD=yourpassword

# ─── MongoDB ─────────────────────────────────────────────────────────────────
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=django_rbac_db
# MONGO_USER=mongouser
# MONGO_PASSWORD=mongopassword

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### .env.example

```env
DJANGO_ENV=development
SECRET_KEY=changeme
JWT_SECRET_KEY=changeme
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_SECONDS=3600
JWT_REFRESH_TOKEN_EXPIRE_SECONDS=2592000
DB_ENGINE=django.db.backends.mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=django_rbac_db
DB_USER=root
DB_PASSWORD=
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=django_rbac_db
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

---

## Settings Configuration

### config/settings/base.py

```python
from pathlib import Path
import environ
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY     = env("SECRET_KEY")
ALLOWED_HOSTS  = env.list("ALLOWED_HOSTS", default=["*"])
AUTH_USER_MODEL = "users.User"

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS = [
    "apps.users",
    "apps.authentication",
    "apps.rbac",
    "apps.activity",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# ── Database — all values from .env ──────────────────────────────────────────
def _build_db() -> dict:
    engine = env("DB_ENGINE", default="django.db.backends.mysql")
    base   = {
        "ENGINE": engine,
        "NAME":   env("DB_NAME", default="django_rbac_db"),
    }
    # SQLite only needs NAME
    if "sqlite" not in engine:
        base.update({
            "HOST":     env("DB_HOST",     default="localhost"),
            "PORT":     env("DB_PORT",     default="3306"),
            "USER":     env("DB_USER",     default="root"),
            "PASSWORD": env("DB_PASSWORD", default=""),
        })
    # MySQL connection settings
    if "mysql" in engine:
        base["OPTIONS"] = {
            "charset":    "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    return base

DATABASES = {"default": _build_db()}

# ── JWT — all from .env ──────────────────────────────────────────────────────
JWT_SECRET_KEY               = env("JWT_SECRET_KEY")
JWT_ALGORITHM                = env("JWT_ALGORITHM", default="HS256")
JWT_ACCESS_TOKEN_EXPIRE_SECONDS  = env.int("JWT_ACCESS_TOKEN_EXPIRE_SECONDS",  default=3600)
JWT_REFRESH_TOKEN_EXPIRE_SECONDS = env.int("JWT_REFRESH_TOKEN_EXPIRE_SECONDS", default=2592000)

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_HOST     = env("MONGO_HOST",     default="localhost")
MONGO_PORT     = env.int("MONGO_PORT", default=27017)
MONGO_DB       = env("MONGO_DB",       default="django_rbac_db")
MONGO_USER     = env("MONGO_USER",     default=None)
MONGO_PASSWORD = env("MONGO_PASSWORD", default=None)

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],  # PyJWT — no DRF auth backend
    "DEFAULT_PERMISSION_CLASSES":     ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS":       "core.pagination.StandardPagination",
    "PAGE_SIZE":                      10,
    "DEFAULT_FILTER_BACKENDS":        [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS  = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CORS_ALLOW_CREDENTIALS = True

STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

### config/settings/development.py

```python
from .base import *
DEBUG = True
```

### config/settings/production.py

```python
from .base import *
DEBUG = False
SECURE_SSL_REDIRECT   = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE    = True
```

---

## Models & Schema Design

### apps/users/models.py

```python
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra):
        email = self.normalize_email(email)
        user  = self.model(email=email, username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra):
        extra.setdefault("is_staff",     True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    username   = models.CharField(max_length=80,  unique=True)
    email      = models.EmailField(unique=True)
    first_name = models.CharField(max_length=80,  blank=True)
    last_name  = models.CharField(max_length=80,  blank=True)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["username"]
    objects = UserManager()

    class Meta:
        db_table = "users"

    def get_all_permissions_rbac(self) -> set:
        perms = set()
        for ur in self.user_roles.select_related("role").prefetch_related("role__role_permissions__permission"):
            for rp in ur.role.role_permissions.all():
                p = rp.permission
                perms.add(f"{p.resource}:{p.action}")
        return perms

    def has_rbac_permission(self, resource: str, action: str) -> bool:
        return f"{resource}:{action}" in self.get_all_permissions_rbac()

    def has_rbac_role(self, role_name: str) -> bool:
        return self.user_roles.filter(role__name=role_name).exists()

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "username":    self.username,
            "email":       self.email,
            "first_name":  self.first_name,
            "last_name":   self.last_name,
            "is_active":   self.is_active,
            "roles":       list(self.user_roles.values_list("role__name", flat=True)),
            "permissions": list(self.get_all_permissions_rbac()),
            "created_at":  self.created_at.isoformat(),
        }
```

### apps/rbac/models.py

```python
from django.db import models
from django.conf import settings
from django.utils import timezone


class Permission(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    resource    = models.CharField(max_length=100)
    action      = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table        = "rbac_permissions"
        unique_together = ("resource", "action")

    def __str__(self):
        return f"{self.resource}:{self.action}"

    def to_dict(self):
        return {"id": self.id, "name": self.name, "resource": self.resource,
                "action": self.action, "description": self.description}


class Role(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rbac_roles"

    def __str__(self):
        return self.name

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "permissions": [rp.permission.to_dict() for rp in self.role_permissions.select_related("permission")],
        }


class RolePermission(models.Model):
    role       = models.ForeignKey(Role,       on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")
    granted_at = models.DateTimeField(default=timezone.now)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="granted_role_permissions")

    class Meta:
        db_table        = "rbac_role_permissions"
        unique_together = ("role", "permission")


class UserRole(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_roles")
    role        = models.ForeignKey(Role,                     on_delete=models.CASCADE, related_name="user_roles")
    assigned_at = models.DateTimeField(default=timezone.now)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="assigned_user_roles")

    class Meta:
        db_table        = "rbac_user_roles"
        unique_together = ("user", "role")
```

### apps/authentication/models.py

```python
from django.db import models
from django.utils import timezone


class TokenBlacklist(models.Model):
    """DB-backed JWT revocation — survives server restarts."""
    jti        = models.CharField(max_length=36, unique=True, db_index=True)
    token_type = models.CharField(max_length=20, default="access")
    revoked_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "token_blacklist"

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        return cls.objects.filter(jti=jti).exists()

    @classmethod
    def revoke(cls, jti: str, token_type: str, expires_at):
        if not cls.is_revoked(jti):
            cls.objects.create(jti=jti, token_type=token_type, expires_at=expires_at)
```

---

## JWT Implementation (PyJWT)

### apps/authentication/jwt_utils.py

```python
"""
PyJWT-based token helpers for Django.
All config is read from Django settings (which load from .env).
"""

import jwt
import uuid
from datetime import datetime, timezone, timedelta
from django.conf import settings


def _secret() -> str:
    return settings.JWT_SECRET_KEY


def _algorithm() -> str:
    return settings.JWT_ALGORITHM


def create_access_token(user_id: int, extra: dict = {}) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS)
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
    expires = now + timedelta(seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_SECONDS)
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
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, _secret(), algorithms=[_algorithm()])


def extract_bearer(header_value: str) -> str:
    if header_value and header_value.startswith("Bearer "):
        return header_value[7:]
    return header_value or ""
```

---

## Auth Middleware Decorator

### apps/authentication/middleware.py

```python
"""
PyJWT decorator — exactly matching the decorator pattern in the project spec.

Spec pattern:
    def jwt_required(func):
        def wrapper(self, request, *args, **kwargs):
            token = request.headers.get("Authorization")
            ...
            teacher = Teacher.objects.get(t_id=payload["t_id"])
            request.user = teacher

Here we generalise it for the User model with full RBAC support.

Usage:
    class UserViewSet(ViewSet):

        @jwt_required
        def list(self, request):
            user = request.user   # ← User instance attached here

        @permission_required("users", "delete")
        def destroy(self, request, pk=None): ...

        @role_required("admin")
        def admin_action(self, request): ...
"""

import jwt as pyjwt
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timezone

from apps.users.models           import User
from apps.authentication.models  import TokenBlacklist
from apps.authentication.jwt_utils import decode_token, extract_bearer


# ─────────────────────────────────────────────────────────────────────────────
# Core: jwt_required  (matches spec pattern exactly)
# ─────────────────────────────────────────────────────────────────────────────

def jwt_required(func):
    """
    Verify the Bearer JWT on every request.
    Attaches the authenticated User instance to request.user.
    Works for both function-based views and class-based view methods.
    """
    @wraps(func)
    def wrapper(self_or_request, request_or_none=None, *args, **kwargs):
        # Support both: standalone view (request=first arg)
        # and class-based view (self=first, request=second)
        if request_or_none is None:
            request = self_or_request
            _self   = None
        else:
            request = request_or_none
            _self   = self_or_request

        token = request.headers.get("Authorization", "")
        if not token:
            return Response({"error": "Token is missing"}, status=status.HTTP_401_UNAUTHORIZED)

        if token.startswith("Bearer "):
            token = token[7:]   # remove 'Bearer ' prefix  ← spec pattern

        try:
            payload = decode_token(token)
        except pyjwt.ExpiredSignatureError:
            return Response({"error": "Token has expired"},   status=status.HTTP_401_UNAUTHORIZED)
        except pyjwt.InvalidTokenError:
            return Response({"error": "Invalid token"},       status=status.HTTP_401_UNAUTHORIZED)

        if payload.get("type") != "access":
            return Response({"error": "Access token required"}, status=status.HTTP_401_UNAUTHORIZED)

        # DB-backed blacklist check
        if TokenBlacklist.is_revoked(payload["jti"]):
            return Response({"error": "Token has been revoked"}, status=status.HTTP_401_UNAUTHORIZED)

        # Load user from DB  ← spec: Teacher.objects.get(t_id=payload["t_id"])
        try:
            user = User.objects.get(id=int(payload["sub"]))
        except (User.DoesNotExist, ValueError):
            return Response({"error": "User not found"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account is disabled"}, status=status.HTTP_403_FORBIDDEN)

        request.user         = user     # ← attach to request  (spec pattern)
        request.token_payload = payload

        if _self is not None:
            return func(_self, request, *args, **kwargs)
        return func(request, *args, **kwargs)

    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# RBAC: permission_required
# ─────────────────────────────────────────────────────────────────────────────

def permission_required(resource: str, action: str):
    def decorator(func):
        @wraps(func)
        @jwt_required
        def wrapper(self_or_request, request_or_none=None, *args, **kwargs):
            request = request_or_none if request_or_none is not None else self_or_request
            if not request.user.has_rbac_permission(resource, action):
                return Response(
                    {"error": "Forbidden", "required": f"{resource}:{action}"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if request_or_none is not None:
                return func(self_or_request, request, *args, **kwargs)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# RBAC: role_required
# ─────────────────────────────────────────────────────────────────────────────

def role_required(*role_names: str):
    def decorator(func):
        @wraps(func)
        @jwt_required
        def wrapper(self_or_request, request_or_none=None, *args, **kwargs):
            request = request_or_none if request_or_none is not None else self_or_request
            if not any(request.user.has_rbac_role(r) for r in role_names):
                return Response(
                    {"error": "Forbidden", "required_roles": list(role_names)},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if request_or_none is not None:
                return func(self_or_request, request, *args, **kwargs)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
```

---

## Authentication Views

### apps/authentication/views.py

```python
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from django.conf import settings

from apps.users.models          import User
from .models                    import TokenBlacklist
from .jwt_utils                 import (
    create_access_token, create_refresh_token,
    decode_token, extract_bearer,
)
from .middleware                import jwt_required
from apps.users.serializers     import UserRegisterSerializer, UserResponseSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = UserRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(
            {"success": True, "message": "Registered", "data": user.to_dict()},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get("email", "")
        password = request.data.get("password", "")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=401)

        if not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=401)
        if not user.is_active:
            return Response({"error": "Account disabled"}, status=403)

        user.last_login = datetime.now(timezone.utc)
        user.save(update_fields=["last_login"])

        extra = {
            "username":    user.username,
            "roles":       list(user.user_roles.values_list("role__name", flat=True)),
            "permissions": list(user.get_all_permissions_rbac()),
        }
        access_token  = create_access_token(user.id, extra=extra)
        refresh_token = create_refresh_token(user.id)

        return Response({
            "success": True,
            "message": "Login successful",
            "data": {
                "access_token":  access_token,
                "refresh_token": refresh_token,
                "token_type":    "Bearer",
                "user":          user.to_dict(),
            },
        })


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @jwt_required
    def delete(self, request):
        payload    = request.token_payload
        jti        = payload["jti"]
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        TokenBlacklist.revoke(jti=jti, token_type="access", expires_at=expires_at)
        return Response({"success": True, "message": "Logged out"})


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh_token", "")
        try:
            payload = decode_token(refresh_token)
        except pyjwt.ExpiredSignatureError:
            return Response({"error": "Refresh token expired"}, status=401)
        except pyjwt.InvalidTokenError:
            return Response({"error": "Invalid refresh token"}, status=401)

        if payload.get("type") != "refresh":
            return Response({"error": "Refresh token required"}, status=401)
        if TokenBlacklist.is_revoked(payload["jti"]):
            return Response({"error": "Token has been revoked"}, status=401)

        try:
            user = User.objects.get(id=int(payload["sub"]))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        extra = {
            "username":    user.username,
            "roles":       list(user.user_roles.values_list("role__name", flat=True)),
            "permissions": list(user.get_all_permissions_rbac()),
        }
        return Response({"success": True, "data": {
            "access_token": create_access_token(user.id, extra=extra),
            "token_type":   "Bearer",
        }})


class MeView(APIView):
    permission_classes = [AllowAny]

    @jwt_required
    def get(self, request):
        return Response({"success": True, "data": request.user.to_dict()})
```

### apps/authentication/urls.py

```python
from django.urls import path
from .views import RegisterView, LoginView, LogoutView, RefreshView, MeView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/",    LoginView.as_view(),    name="login"),
    path("logout/",   LogoutView.as_view(),   name="logout"),
    path("refresh/",  RefreshView.as_view(),  name="refresh"),
    path("me/",       MeView.as_view(),       name="me"),
]
```

---

## DRF Permission Classes

### apps/rbac/permissions.py

```python
from rest_framework.permissions import BasePermission


class HasRBACPermission(BasePermission):
    """
    Works with ViewSets that declare:
        rbac_resource  = "users"
        rbac_action_map = {"list": "read", "create": "create", ...}
    """
    def has_permission(self, request, view):
        if not hasattr(request, "user") or not request.user:
            return False
        resource   = getattr(view, "rbac_resource",  None)
        action_map = getattr(view, "rbac_action_map", {})
        action     = action_map.get(view.action, view.action)
        if not resource or not action:
            return True
        return request.user.has_rbac_permission(resource, action)


class IsAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if not hasattr(request, "user") or not request.user:
            return False
        return (
            request.user.has_rbac_role("admin")
            or request.user.has_rbac_role("super_admin")
            or request.user.is_superuser
        )
```

---

## CRUD ViewSets

### apps/users/views.py

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import User
from .serializers import UserRegisterSerializer, UserUpdateSerializer, UserResponseSerializer
from apps.rbac.models import Role, UserRole
from apps.rbac.permissions import HasRBACPermission, IsAdminOrSuperAdmin
from apps.authentication.middleware import jwt_required


class UserViewSet(viewsets.ModelViewSet):
    queryset           = User.objects.all().order_by("-created_at")
    permission_classes = [AllowAny]   # JWT enforced via @jwt_required per method

    rbac_resource  = "users"
    rbac_action_map = {
        "list": "read", "retrieve": "read",
        "create": "create", "update": "update",
        "partial_update": "update", "destroy": "delete",
    }

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegisterSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserResponseSerializer

    @jwt_required
    def list(self, request):
        if not request.user.has_rbac_permission("users", "read"):
            return Response({"error": "Forbidden"}, status=403)
        search   = request.query_params.get("search", "")
        page     = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 10))
        qs       = User.objects.all()
        if search:
            qs = qs.filter(username__icontains=search) | qs.filter(email__icontains=search)
        total   = qs.count()
        users   = qs[(page - 1) * per_page: page * per_page]
        return Response({
            "success": True,
            "data": {
                "users":    [u.to_dict() for u in users],
                "total":    total,
                "page":     page,
                "pages":    (total + per_page - 1) // per_page,
                "per_page": per_page,
            }
        })

    @jwt_required
    def retrieve(self, request, pk=None):
        if not request.user.has_rbac_permission("users", "read"):
            return Response({"error": "Forbidden"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
        return Response({"success": True, "data": user.to_dict()})

    @jwt_required
    def create(self, request):
        if not request.user.has_rbac_permission("users", "create"):
            return Response({"error": "Forbidden"}, status=403)
        ser = UserRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response({"success": True, "data": user.to_dict()}, status=201)

    @jwt_required
    def update(self, request, pk=None, partial=False):
        if not request.user.has_rbac_permission("users", "update"):
            return Response({"error": "Forbidden"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
        ser = UserUpdateSerializer(user, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"success": True, "data": user.to_dict()})

    def partial_update(self, request, pk=None):
        return self.update(request, pk=pk, partial=True)

    @jwt_required
    def destroy(self, request, pk=None):
        if not request.user.has_rbac_permission("users", "delete"):
            return Response({"error": "Forbidden"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
        user.delete()
        return Response({"success": True, "message": "User deleted"}, status=204)

    @action(detail=True, methods=["POST"], url_path="roles")
    @jwt_required
    def assign_role(self, request, pk=None):
        if not (request.user.has_rbac_role("admin") or request.user.has_rbac_role("super_admin")):
            return Response({"error": "Forbidden"}, status=403)
        try:
            user = User.objects.get(pk=pk)
            role = Role.objects.get(id=request.data.get("role_id"))
        except (User.DoesNotExist, Role.DoesNotExist) as e:
            return Response({"error": str(e)}, status=404)
        UserRole.objects.get_or_create(user=user, role=role, defaults={"assigned_by": request.user})
        return Response({"success": True, "data": user.to_dict()})

    @action(detail=True, methods=["DELETE"], url_path=r"roles/(?P<role_id>[^/.]+)")
    @jwt_required
    def remove_role(self, request, pk=None, role_id=None):
        if not (request.user.has_rbac_role("admin") or request.user.has_rbac_role("super_admin")):
            return Response({"error": "Forbidden"}, status=403)
        UserRole.objects.filter(user_id=pk, role_id=role_id).delete()
        user = User.objects.get(pk=pk)
        return Response({"success": True, "data": user.to_dict()})
```

---

## MongoDB Integration

### apps/activity/mongo_models.py

```python
import mongoengine
from django.conf import settings
from datetime import datetime


def _build_mongo_uri():
    user     = settings.MONGO_USER
    password = settings.MONGO_PASSWORD
    host     = settings.MONGO_HOST
    port     = settings.MONGO_PORT
    db       = settings.MONGO_DB
    if user and password:
        return f"mongodb://{user}:{password}@{host}:{port}/{db}"
    return f"mongodb://{host}:{port}/{db}"


mongoengine.connect(host=_build_mongo_uri())


class UserActivity(mongoengine.Document):
    user_id    = mongoengine.StringField(required=True)
    action     = mongoengine.StringField(required=True)
    resource   = mongoengine.StringField()
    metadata   = mongoengine.DictField()
    ip_address = mongoengine.StringField()
    created_at = mongoengine.DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "user_activities",
        "indexes":    ["user_id", "-created_at"],
    }
```

---

## Management Command — Seed RBAC

### apps/rbac/management/commands/seed_rbac.py

```python
from django.core.management.base import BaseCommand
from apps.rbac.models import Permission, Role, RolePermission

PERMISSIONS = [
    ("users:read",        "users",       "read"),
    ("users:create",      "users",       "create"),
    ("users:update",      "users",       "update"),
    ("users:delete",      "users",       "delete"),
    ("roles:read",        "roles",       "read"),
    ("roles:create",      "roles",       "create"),
    ("roles:update",      "roles",       "update"),
    ("roles:delete",      "roles",       "delete"),
    ("permissions:read",  "permissions", "read"),
    ("permissions:create","permissions", "create"),
]

ROLE_PERMISSIONS = {
    "super_admin": [p[0] for p in PERMISSIONS],
    "admin":       ["users:read", "users:create", "users:update",
                    "roles:read", "permissions:read"],
    "viewer":      ["users:read", "roles:read", "permissions:read"],
}


class Command(BaseCommand):
    help = "Seed initial RBAC permissions and roles"

    def handle(self, *args, **kwargs):
        for name, resource, action in PERMISSIONS:
            Permission.objects.get_or_create(
                name=name,
                defaults={"resource": resource, "action": action},
            )
        self.stdout.write(self.style.SUCCESS(f"✅ {len(PERMISSIONS)} permissions seeded"))

        for role_name, perm_names in ROLE_PERMISSIONS.items():
            role, _ = Role.objects.get_or_create(name=role_name)
            for perm_name in perm_names:
                try:
                    perm = Permission.objects.get(name=perm_name)
                    RolePermission.objects.get_or_create(role=role, permission=perm)
                except Permission.DoesNotExist:
                    pass
            self.stdout.write(self.style.SUCCESS(f"✅ Role '{role_name}' seeded"))
```

```bash
# MySQL: create the database first
mysql -u root -p -e "CREATE DATABASE django_rbac_db CHARACTER SET utf8mb4;"

python manage.py migrate
python manage.py seed_rbac
python manage.py runserver 0.0.0.0:8000
```

---

## Config URLs

### config/urls.py

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/",         admin.site.urls),
    path("api/auth/",      include("apps.authentication.urls")),
    path("api/users/",     include("apps.users.urls")),
    path("api/",           include("apps.rbac.urls")),
]
```

---

## API Endpoint Summary

| Method | Endpoint | Description | Guard |
|--------|----------|-------------|-------|
| POST | /api/auth/register/ | Register | Public |
| POST | /api/auth/login/ | Login → JWT tokens | Public |
| DELETE | /api/auth/logout/ | Revoke access token | jwt_required |
| POST | /api/auth/refresh/ | New access token | Public |
| GET | /api/auth/me/ | Current user info | jwt_required |
| GET | /api/users/ | List users | permission: users:read |
| POST | /api/users/ | Create user | permission: users:create |
| GET | /api/users/\<id\>/ | Get user | permission: users:read |
| PUT | /api/users/\<id\>/ | Update user | permission: users:update |
| PATCH | /api/users/\<id\>/ | Partial update | permission: users:update |
| DELETE | /api/users/\<id\>/ | Delete user | permission: users:delete |
| POST | /api/users/\<id\>/roles/ | Assign role | role: admin |
| DELETE | /api/users/\<id\>/roles/\<rid\>/ | Remove role | role: admin |
| GET | /api/roles/ | List roles | permission: roles:read |
| POST | /api/roles/ | Create role | permission: roles:create |
| PUT | /api/roles/\<id\>/ | Update role | permission: roles:update |
| DELETE | /api/roles/\<id\>/ | Delete role | permission: roles:delete |
| POST | /api/roles/\<id\>/permissions/ | Assign permission | permission: roles:update |
| DELETE | /api/roles/\<id\>/permissions/\<pid\>/ | Remove permission | permission: roles:update |
| GET | /api/permissions/ | List permissions | permission: permissions:read |
| POST | /api/permissions/ | Create permission | permission: permissions:create |
