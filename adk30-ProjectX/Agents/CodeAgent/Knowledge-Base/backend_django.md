# Django Backend — Production Guide

> PyJWT · MySQL default · `.env` credentials · Custom RBAC · Django REST Framework · Windows + Linux compatible

---

## Verified Package Versions (Python 3.11.x)

```txt
# requirements.txt
Django==5.0.7
djangorestframework==3.15.2
django-cors-headers==4.4.0
django-environ==0.11.2
PyJWT==2.8.0
mysqlclient==2.2.4
mongoengine==0.28.2
gunicorn==22.0.0
```

---

## Project Structure

```
django_project/
├── core/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── authentication/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── middleware.py
│   │   ├── jwt_utils.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   ├── users/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── urls.py
│   └── rbac/
│       ├── __init__.py
│       ├── models.py
│       ├── views.py
│       ├── serializers.py
│       ├── urls.py
│       └── management/
│           ├── __init__.py
│           └── commands/
│               ├── __init__.py
│               └── seed_rbac.py
├── manage.py
├── .env
├── .env.example
└── requirements.txt
```

---

## Minimum Steps to Run (Windows CMD)

```cmd
:: Step 1 — Create project and venv
mkdir django_project
cd django_project
py -3.11 -m venv venv
venv\Scripts\activate

:: Step 2 — Install packages
pip install -r requirements.txt

:: Step 3 — Create MySQL database
mysql -u root -p -e "CREATE DATABASE django_rbac_db CHARACTER SET utf8mb4;"

:: Step 4 — Copy .env (Windows)
copy .env.example .env
:: Edit .env and set DB_PASSWORD, DJANGO_SECRET_KEY, JWT_SECRET_KEY

:: Step 5 — Run migrations
python manage.py migrate

:: Step 6 — Seed RBAC (creates roles + permissions)
python manage.py seed_rbac

:: Step 7 — Run server
python manage.py runserver 0.0.0.0:8000
:: → http://localhost:8000
```

---

## .env

```env
DJANGO_ENV=development
DJANGO_SECRET_KEY=django-secret-min-50-chars-change-this-now
ALLOWED_HOSTS=localhost,127.0.0.1

JWT_SECRET_KEY=jwt-secret-min-64-chars-change-this-now
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_SECONDS=3600
JWT_REFRESH_TOKEN_EXPIRE_SECONDS=2592000

DB_ENGINE=django.db.backends.mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=django_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=django_rbac_db

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

## .env.example

```env
DJANGO_ENV=development
DJANGO_SECRET_KEY=changeme
ALLOWED_HOSTS=localhost,127.0.0.1
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

## core/settings.py

```python
import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY    = env("DJANGO_SECRET_KEY")
DEBUG         = env("DJANGO_ENV", default="development") == "development"
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

AUTH_USER_MODEL = "users.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.users",
    "apps.authentication",
    "apps.rbac",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": [
                  "django.template.context_processors.debug",
                  "django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages",
              ]}}]

WSGI_APPLICATION = "core.wsgi.application"


def _build_db():
    engine = env("DB_ENGINE", default="django.db.backends.mysql")
    base   = {"ENGINE": engine, "NAME": env("DB_NAME", default="django_rbac_db")}
    if "sqlite" not in engine:
        base.update({
            "HOST":     env("DB_HOST",     default="localhost"),
            "PORT":     env("DB_PORT",     default="3306"),
            "USER":     env("DB_USER",     default="root"),
            "PASSWORD": env("DB_PASSWORD", default=""),
        })
    if "mysql" in engine:
        base["OPTIONS"] = {"charset": "utf8mb4",
                           "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"}
    return base


DATABASES = {"default": _build_db()}

# JWT — read from .env
JWT_SECRET_KEY               = env("JWT_SECRET_KEY")
JWT_ALGORITHM                = env("JWT_ALGORITHM", default="HS256")
JWT_ACCESS_TOKEN_EXPIRE_SECONDS  = env.int("JWT_ACCESS_TOKEN_EXPIRE_SECONDS",  default=3600)
JWT_REFRESH_TOKEN_EXPIRE_SECONDS = env.int("JWT_REFRESH_TOKEN_EXPIRE_SECONDS", default=2592000)

# MongoDB
MONGO_HOST     = env("MONGO_HOST",     default="localhost")
MONGO_PORT     = env.int("MONGO_PORT", default=27017)
MONGO_DB       = env("MONGO_DB",       default="django_rbac_db")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "EXCEPTION_HANDLER": "apps.authentication.views.custom_exception_handler",
}

# CORS — split comma string
CORS_ALLOWED_ORIGINS  = [o.strip() for o in env("CORS_ALLOWED_ORIGINS", default="http://localhost:3000").split(",")]
CORS_ALLOW_CREDENTIALS = True

LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True
STATIC_URL    = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

---

## core/urls.py

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/",             admin.site.urls),
    path("api/auth/",          include("apps.authentication.urls")),
    path("api/users/",         include("apps.users.urls")),
    path("api/",               include("apps.rbac.urls")),
]
```

---

## apps/users/models.py

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
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    username    = models.CharField(max_length=80, unique=True)
    email       = models.EmailField(unique=True)
    first_name  = models.CharField(max_length=80, blank=True)
    last_name   = models.CharField(max_length=80, blank=True)
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)
    last_login  = models.DateTimeField(null=True, blank=True)

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

    def to_dict(self):
        return {
            "id": self.id, "username": self.username, "email": self.email,
            "first_name": self.first_name, "last_name": self.last_name,
            "is_active": self.is_active,
            "roles": list(self.user_roles.values_list("role__name", flat=True)),
            "permissions": list(self.get_all_permissions_rbac()),
            "created_at": self.created_at.isoformat(),
        }
```

---

## apps/users/serializers.py

```python
from rest_framework import serializers
from .models import User


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = User
        fields = ("username", "email", "password", "first_name", "last_name")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user     = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model  = User
        fields = ("first_name", "last_name", "is_active", "password")

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
```

---

## apps/users/urls.py

```python
from django.urls import path
from .views import UserListCreateView, UserDetailView, UserRoleView, UserRoleDetailView

urlpatterns = [
    path("",                             UserListCreateView.as_view(),  name="user-list"),
    path("<int:pk>/",                    UserDetailView.as_view(),      name="user-detail"),
    path("<int:pk>/roles/",              UserRoleView.as_view(),        name="user-role"),
    path("<int:pk>/roles/<int:role_id>/", UserRoleDetailView.as_view(), name="user-role-detail"),
]
```

---

## apps/users/views.py

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.authentication.middleware import jwt_required, permission_required, role_required
from apps.rbac.models import Role, UserRole
from .models import User
from .serializers import UserRegisterSerializer, UserUpdateSerializer


class UserListCreateView(APIView):

    @jwt_required
    def get(self, request):
        if not request.user.has_rbac_permission("users", "read"):
            return Response({"error": "Forbidden"}, status=403)
        search   = request.query_params.get("search", "")
        page     = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 10))
        qs       = User.objects.all()
        if search:
            qs = qs.filter(username__icontains=search) | qs.filter(email__icontains=search)
        total = qs.count()
        users = qs[(page - 1) * per_page: page * per_page]
        return Response({"success": True, "data": {
            "users": [u.to_dict() for u in users],
            "total": total, "page": page,
            "pages": (total + per_page - 1) // per_page, "per_page": per_page,
        }})

    @jwt_required
    def post(self, request):
        if not request.user.has_rbac_permission("users", "create"):
            return Response({"error": "Forbidden"}, status=403)
        ser = UserRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response({"success": True, "data": user.to_dict()}, status=201)


class UserDetailView(APIView):

    def _get_user(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    @jwt_required
    def get(self, request, pk):
        if not request.user.has_rbac_permission("users", "read"):
            return Response({"error": "Forbidden"}, status=403)
        user = self._get_user(pk)
        if not user:
            return Response({"error": "Not found"}, status=404)
        return Response({"success": True, "data": user.to_dict()})

    @jwt_required
    def put(self, request, pk):
        if not request.user.has_rbac_permission("users", "update"):
            return Response({"error": "Forbidden"}, status=403)
        user = self._get_user(pk)
        if not user:
            return Response({"error": "Not found"}, status=404)
        ser = UserUpdateSerializer(user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"success": True, "data": user.to_dict()})

    @jwt_required
    def delete(self, request, pk):
        if not request.user.has_rbac_permission("users", "delete"):
            return Response({"error": "Forbidden"}, status=403)
        user = self._get_user(pk)
        if not user:
            return Response({"error": "Not found"}, status=404)
        user.delete()
        return Response({"success": True, "message": "Deleted"}, status=204)


class UserRoleView(APIView):

    @jwt_required
    def post(self, request, pk):
        if not (request.user.has_rbac_role("admin") or request.user.has_rbac_role("super_admin")):
            return Response({"error": "Forbidden"}, status=403)
        try:
            user = User.objects.get(pk=pk)
            role = Role.objects.get(id=request.data.get("role_id"))
        except (User.DoesNotExist, Role.DoesNotExist):
            return Response({"error": "Not found"}, status=404)
        UserRole.objects.get_or_create(user=user, role=role)
        return Response({"success": True, "data": user.to_dict()})


class UserRoleDetailView(APIView):

    @jwt_required
    def delete(self, request, pk, role_id):
        if not (request.user.has_rbac_role("admin") or request.user.has_rbac_role("super_admin")):
            return Response({"error": "Forbidden"}, status=403)
        UserRole.objects.filter(user_id=pk, role_id=role_id).delete()
        user = User.objects.get(pk=pk)
        return Response({"success": True, "data": user.to_dict()})
```

---

## apps/authentication/models.py

```python
from django.db import models
from django.utils import timezone


class TokenBlacklist(models.Model):
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

## apps/authentication/jwt_utils.py

```python
import jwt
import uuid
from datetime import datetime, timezone, timedelta
from django.conf import settings


def create_access_token(user_id: int, extra: dict = {}) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_SECONDS)
    payload = {"sub": str(user_id), "jti": str(uuid.uuid4()),
               "type": "access", "iat": now, "exp": expires, **extra}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_SECONDS)
    payload = {"sub": str(user_id), "jti": str(uuid.uuid4()),
               "type": "refresh", "iat": now, "exp": expires}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def extract_bearer(header_value: str) -> str:
    if header_value and header_value.startswith("Bearer "):
        return header_value[7:]
    return header_value or ""
```

---

## apps/authentication/middleware.py

```python
import jwt as pyjwt
from functools import wraps
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import User
from .models import TokenBlacklist
from .jwt_utils import decode_token, extract_bearer


def jwt_required(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        token = extract_bearer(request.headers.get("Authorization", ""))
        if not token:
            return Response({"error": "Token is missing"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            payload = decode_token(token)
        except pyjwt.ExpiredSignatureError:
            return Response({"error": "Token has expired"}, status=status.HTTP_401_UNAUTHORIZED)
        except pyjwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        if payload.get("type") != "access":
            return Response({"error": "Access token required"}, status=status.HTTP_401_UNAUTHORIZED)
        if TokenBlacklist.is_revoked(payload["jti"]):
            return Response({"error": "Token has been revoked"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(id=int(payload["sub"]))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"error": "Account is disabled"}, status=status.HTTP_403_FORBIDDEN)

        request.user          = user
        request.token_payload = payload
        return func(self, request, *args, **kwargs)
    return wrapper


def permission_required(resource: str, action: str):
    def decorator(func):
        @wraps(func)
        @jwt_required
        def wrapper(self, request, *args, **kwargs):
            if not request.user.has_rbac_permission(resource, action):
                return Response({"error": "Forbidden", "required": f"{resource}:{action}"},
                                status=status.HTTP_403_FORBIDDEN)
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def role_required(*role_names: str):
    def decorator(func):
        @wraps(func)
        @jwt_required
        def wrapper(self, request, *args, **kwargs):
            if not any(request.user.has_rbac_role(r) for r in role_names):
                return Response({"error": "Forbidden", "required_roles": list(role_names)},
                                status=status.HTTP_403_FORBIDDEN)
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator
```

---

## apps/authentication/views.py

```python
import jwt as pyjwt
from datetime import datetime, timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from apps.users.models import User
from apps.users.serializers import UserRegisterSerializer
from .models import TokenBlacklist
from .jwt_utils import create_access_token, create_refresh_token, decode_token, extract_bearer
from .middleware import jwt_required


def custom_exception_handler(exc, context):
    from rest_framework.views import exception_handler
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {"success": False, "message": str(exc), "errors": response.data}
    return response


class RegisterView(APIView):
    def post(self, request):
        ser = UserRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response({"success": True, "data": user.to_dict()}, status=201)


class LoginView(APIView):
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

        extra = {"username": user.username,
                 "roles": list(user.user_roles.values_list("role__name", flat=True)),
                 "permissions": list(user.get_all_permissions_rbac())}
        return Response({"success": True, "data": {
            "access_token":  create_access_token(user.id, extra=extra),
            "refresh_token": create_refresh_token(user.id),
            "token_type":    "Bearer",
            "user":          user.to_dict(),
        }})


class LogoutView(APIView):
    @jwt_required
    def delete(self, request):
        payload    = request.token_payload
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        TokenBlacklist.revoke(jti=payload["jti"], token_type="access", expires_at=expires_at)
        return Response({"success": True, "message": "Logged out"})


class RefreshView(APIView):
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
            return Response({"error": "Token revoked"}, status=401)
        try:
            user = User.objects.get(id=int(payload["sub"]))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        extra = {"username": user.username,
                 "roles": list(user.user_roles.values_list("role__name", flat=True)),
                 "permissions": list(user.get_all_permissions_rbac())}
        return Response({"success": True, "data": {
            "access_token": create_access_token(user.id, extra=extra), "token_type": "Bearer"
        }})


class MeView(APIView):
    @jwt_required
    def get(self, request):
        return Response({"success": True, "data": request.user.to_dict()})
```

---

## apps/authentication/urls.py

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

## apps/rbac/models.py

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

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description,
                "permissions": [rp.permission.to_dict()
                                for rp in self.role_permissions.select_related("permission")]}


class RolePermission(models.Model):
    role       = models.ForeignKey(Role,       on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="role_permissions")
    granted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table        = "rbac_role_permissions"
        unique_together = ("role", "permission")


class UserRole(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_roles")
    role        = models.ForeignKey(Role,                     on_delete=models.CASCADE, related_name="user_roles")
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table        = "rbac_user_roles"
        unique_together = ("user", "role")
```

---

## apps/rbac/views.py

```python
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.authentication.middleware import permission_required, role_required
from .models import Permission, Role, RolePermission


class RoleListCreateView(APIView):
    @permission_required("roles", "read")
    def get(self, request):
        return Response({"success": True, "data": [r.to_dict() for r in Role.objects.all()]})

    @permission_required("roles", "create")
    def post(self, request):
        if Role.objects.filter(name=request.data.get("name")).exists():
            return Response({"error": "Role exists"}, status=409)
        role = Role.objects.create(name=request.data["name"],
                                   description=request.data.get("description", ""))
        return Response({"success": True, "data": role.to_dict()}, status=201)


class RoleDetailView(APIView):
    def _get_role(self, pk):
        try:
            return Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return None

    @permission_required("roles", "read")
    def get(self, request, pk):
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=404)
        return Response({"success": True, "data": role.to_dict()})

    @permission_required("roles", "update")
    def put(self, request, pk):
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=404)
        for field in ("name", "description"):
            if field in request.data:
                setattr(role, field, request.data[field])
        role.save()
        return Response({"success": True, "data": role.to_dict()})

    @permission_required("roles", "delete")
    def delete(self, request, pk):
        role = self._get_role(pk)
        if not role:
            return Response({"error": "Not found"}, status=404)
        role.delete()
        return Response({"success": True, "message": "Deleted"}, status=204)


class RolePermissionView(APIView):
    @permission_required("roles", "update")
    def post(self, request, pk):
        try:
            role = Role.objects.get(pk=pk)
            perm = Permission.objects.get(id=request.data.get("permission_id"))
        except (Role.DoesNotExist, Permission.DoesNotExist):
            return Response({"error": "Not found"}, status=404)
        RolePermission.objects.get_or_create(role=role, permission=perm)
        return Response({"success": True, "data": role.to_dict()})


class RolePermissionDetailView(APIView):
    @permission_required("roles", "update")
    def delete(self, request, pk, perm_id):
        RolePermission.objects.filter(role_id=pk, permission_id=perm_id).delete()
        role = Role.objects.get(pk=pk)
        return Response({"success": True, "data": role.to_dict()})


class PermissionListCreateView(APIView):
    @permission_required("permissions", "read")
    def get(self, request):
        return Response({"success": True, "data": [p.to_dict() for p in Permission.objects.all()]})

    @permission_required("permissions", "create")
    def post(self, request):
        perm = Permission.objects.create(
            name=request.data["name"], resource=request.data["resource"],
            action=request.data["action"], description=request.data.get("description", ""))
        return Response({"success": True, "data": perm.to_dict()}, status=201)


class PermissionDetailView(APIView):
    @permission_required("permissions", "update")
    def put(self, request, pk):
        try:
            perm = Permission.objects.get(pk=pk)
        except Permission.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
        for field in ("name", "resource", "action", "description"):
            if field in request.data:
                setattr(perm, field, request.data[field])
        perm.save()
        return Response({"success": True, "data": perm.to_dict()})

    @permission_required("permissions", "delete")
    def delete(self, request, pk):
        try:
            Permission.objects.get(pk=pk).delete()
        except Permission.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
        return Response({"success": True, "message": "Deleted"}, status=204)
```

---

## apps/rbac/urls.py

```python
from django.urls import path
from .views import (RoleListCreateView, RoleDetailView, RolePermissionView,
                    RolePermissionDetailView, PermissionListCreateView, PermissionDetailView)

urlpatterns = [
    path("roles/",                                          RoleListCreateView.as_view()),
    path("roles/<int:pk>/",                                 RoleDetailView.as_view()),
    path("roles/<int:pk>/permissions/",                     RolePermissionView.as_view()),
    path("roles/<int:pk>/permissions/<int:perm_id>/",       RolePermissionDetailView.as_view()),
    path("permissions/",                                    PermissionListCreateView.as_view()),
    path("permissions/<int:pk>/",                           PermissionDetailView.as_view()),
]
```

---

## apps/rbac/management/commands/seed_rbac.py

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
    ("permissions:update","permissions", "update"),
    ("permissions:delete","permissions", "delete"),
]

ROLE_PERMISSIONS = {
    "super_admin": [p[0] for p in PERMISSIONS],
    "admin":       ["users:read","users:create","users:update",
                    "roles:read","permissions:read"],
    "viewer":      ["users:read","roles:read","permissions:read"],
}


class Command(BaseCommand):
    help = "Seed RBAC permissions and roles"

    def handle(self, *args, **kwargs):
        for name, resource, action in PERMISSIONS:
            Permission.objects.get_or_create(name=name, defaults={"resource": resource, "action": action})
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

---

## manage.py

```python
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django.") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

---

## Database Switching (change .env only)

```env
# MySQL (default)
DB_ENGINE=django.db.backends.mysql

# SQLite
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_HOST=localhost
DB_PORT=5432
```

---

## API Endpoints

| Method | URL | Auth |
|--------|-----|------|
| POST | /api/auth/register/ | Public |
| POST | /api/auth/login/ | Public |
| DELETE | /api/auth/logout/ | Bearer |
| POST | /api/auth/refresh/ | Public |
| GET | /api/auth/me/ | Bearer |
| GET | /api/users/ | permission:users:read |
| POST | /api/users/ | permission:users:create |
| GET | /api/users/\<id\>/ | permission:users:read |
| PUT | /api/users/\<id\>/ | permission:users:update |
| DELETE | /api/users/\<id\>/ | permission:users:delete |
| POST | /api/users/\<id\>/roles/ | role:admin |
| DELETE | /api/users/\<id\>/roles/\<rid\>/ | role:admin |
| GET | /api/roles/ | permission:roles:read |
| POST | /api/roles/ | permission:roles:create |
| PUT | /api/roles/\<id\>/ | permission:roles:update |
| DELETE | /api/roles/\<id\>/ | permission:roles:delete |
| POST | /api/roles/\<id\>/permissions/ | permission:roles:update |
| DELETE | /api/roles/\<id\>/permissions/\<pid\>/ | permission:roles:update |
| GET | /api/permissions/ | permission:permissions:read |
| POST | /api/permissions/ | permission:permissions:create |
| PUT | /api/permissions/\<id\>/ | permission:permissions:update |
| DELETE | /api/permissions/\<id\>/ | permission:permissions:delete |
