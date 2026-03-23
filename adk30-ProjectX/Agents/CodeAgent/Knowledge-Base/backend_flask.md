# Flask Backend — Production Guide

> PyJWT · MySQL default · `.env` credentials · Dynamic RBAC · Windows + Linux compatible

---

## Verified Package Versions (Python 3.11.x)

```txt
# requirements.txt
flask==3.0.3
flask-sqlalchemy==3.1.1
flask-migrate==4.0.7
flask-bcrypt==1.0.1
flask-cors==4.0.1
PyJWT==2.8.0
python-decouple==3.8
PyMySQL==1.1.1
cryptography==42.0.8
mongoengine==0.28.2
gunicorn==22.0.0
```

---

## Project Structure

```
flask_project/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   ├── associations.py
│   │   └── token_blacklist.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py
│   │   ├── user_routes.py
│   │   ├── role_routes.py
│   │   └── permission_routes.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   └── role_service.py
│   ├── middleware/
│   │   └── auth_middleware.py
│   └── utils/
│       ├── jwt_utils.py
│       └── response.py
├── migrations/
├── .env
├── .env.example
├── requirements.txt
└── run.py
```

---

## Minimum Steps to Run (Windows CMD)

```cmd
:: Step 1 — Create project folder and venv
mkdir flask_project
cd flask_project
py -3.11 -m venv venv
venv\Scripts\activate

:: Step 2 — Install packages
pip install -r requirements.txt

:: Step 3 — Create MySQL database
mysql -u root -p -e "CREATE DATABASE flask_rbac_db CHARACTER SET utf8mb4;"

:: Step 4 — Copy .env (Windows uses copy, not cp)
copy .env.example .env
:: Now edit .env with your DB_PASSWORD and secrets

:: Step 5 — Run migrations
flask db init
flask db migrate -m "initial schema"
flask db upgrade

:: Step 6 — Run server
python run.py
:: → http://localhost:5000
```

---

## .env

```env
FLASK_ENV=development
SECRET_KEY=flask-secret-key-min-50-chars-change-this-now

JWT_SECRET_KEY=jwt-secret-key-min-64-random-chars-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

DB_DRIVER=mysql+pymysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flask_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=flask_rbac_db

CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## .env.example

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

## app/config.py

```python
import os
from datetime import timedelta
from decouple import config


def _build_db_url() -> str:
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
    SECRET_KEY = config("SECRET_KEY")
    DEBUG      = False

    JWT_SECRET_KEY  = config("JWT_SECRET_KEY")
    JWT_ALGORITHM   = config("JWT_ALGORITHM", default="HS256")
    JWT_ACCESS_TTL  = timedelta(seconds=config("JWT_ACCESS_TOKEN_EXPIRES",  cast=int, default=3600))
    JWT_REFRESH_TTL = timedelta(seconds=config("JWT_REFRESH_TOKEN_EXPIRES", cast=int, default=2592000))

    SQLALCHEMY_DATABASE_URI        = _build_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_RECYCLE        = 280
    SQLALCHEMY_POOL_PRE_PING       = True

    MONGO_URI = _build_mongo_uri()

    # Split comma-separated string — avoids JSON parsing errors
    CORS_ORIGINS = [o.strip() for o in config("CORS_ORIGINS", default="http://localhost:3000").split(",")]


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
}
```

---

## app/extensions.py

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

---

## app/__init__.py

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

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    try:
        mongoengine.connect(host=app.config["MONGO_URI"])
    except Exception:
        pass  # MongoDB optional for development

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

## app/models/associations.py

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

---

## app/models/permission.py

```python
from ..extensions import db
from datetime import datetime


class Permission(db.Model):
    __tablename__ = "permissions"
    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(100), unique=True,  nullable=False)
    resource    = db.Column(db.String(100), nullable=False)
    action      = db.Column(db.String(50),  nullable=False)
    description = db.Column(db.String(255))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    roles = db.relationship("Role", secondary="role_permissions", back_populates="permissions")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "resource": self.resource,
                "action": self.action, "description": self.description,
                "created_at": self.created_at.isoformat()}
```

---

## app/models/role.py

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
        return {"id": self.id, "name": self.name, "description": self.description,
                "permissions": [p.to_dict() for p in self.permissions],
                "created_at": self.created_at.isoformat()}
```

---

## app/models/user.py

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
from ..extensions import db
from datetime import datetime


class TokenBlacklist(db.Model):
    __tablename__ = "token_blacklist"
    id         = db.Column(db.Integer,    primary_key=True)
    jti        = db.Column(db.String(36), unique=True, nullable=False, index=True)
    token_type = db.Column(db.String(20), default="access")
    revoked_at = db.Column(db.DateTime,   default=datetime.utcnow)
    expires_at = db.Column(db.DateTime,   nullable=False)

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        return db.session.query(cls.id).filter_by(jti=jti).first() is not None

    @classmethod
    def revoke(cls, jti: str, token_type: str, expires_at: datetime):
        if not cls.is_revoked(jti):
            db.session.add(cls(jti=jti, token_type=token_type, expires_at=expires_at))
            db.session.commit()
```

---

## app/models/__init__.py

```python
from .user          import User
from .role          import Role
from .permission    import Permission
from .token_blacklist import TokenBlacklist
from .associations  import role_permissions, user_roles
```

---

## app/utils/jwt_utils.py

```python
import jwt
import uuid
from datetime import datetime, timezone
from flask import current_app


def create_access_token(user_id: int, extra: dict = {}) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + current_app.config["JWT_ACCESS_TTL"]
    payload = {
        "sub": str(user_id), "jti": str(uuid.uuid4()),
        "type": "access", "iat": now, "exp": expires,
        **extra,
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"],
                      algorithm=current_app.config["JWT_ALGORITHM"])


def create_refresh_token(user_id: int) -> str:
    now     = datetime.now(timezone.utc)
    expires = now + current_app.config["JWT_REFRESH_TTL"]
    payload = {"sub": str(user_id), "jti": str(uuid.uuid4()),
               "type": "refresh", "iat": now, "exp": expires}
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"],
                      algorithm=current_app.config["JWT_ALGORITHM"])


def decode_token(token: str) -> dict:
    return jwt.decode(token, current_app.config["JWT_SECRET_KEY"],
                      algorithms=[current_app.config["JWT_ALGORITHM"]])


def extract_bearer(header_value: str) -> str:
    if header_value and header_value.startswith("Bearer "):
        return header_value[7:]
    return header_value or ""
```

---

## app/middleware/auth_middleware.py

```python
import jwt as pyjwt
from functools import wraps
from flask import request, jsonify, g

from ..models.user           import User
from ..models.token_blacklist import TokenBlacklist
from ..utils.jwt_utils        import decode_token, extract_bearer


def jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = extract_bearer(request.headers.get("Authorization", ""))
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        try:
            payload = decode_token(token)
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        if payload.get("type") != "access":
            return jsonify({"error": "Access token required"}), 401
        if TokenBlacklist.is_revoked(payload["jti"]):
            return jsonify({"error": "Token has been revoked"}), 401

        user = User.query.get(int(payload["sub"]))
        if not user:
            return jsonify({"error": "User not found"}), 401
        if not user.is_active:
            return jsonify({"error": "Account is disabled"}), 403

        g.current_user  = user
        g.token_payload = payload
        return func(*args, **kwargs)
    return wrapper


def permission_required(resource: str, action: str):
    def decorator(func):
        @wraps(func)
        @jwt_required
        def wrapper(*args, **kwargs):
            if not g.current_user.has_permission(resource, action):
                return jsonify({"error": "Forbidden", "required": f"{resource}:{action}"}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator


def role_required(*role_names: str):
    def decorator(func):
        @wraps(func)
        @jwt_required
        def wrapper(*args, **kwargs):
            if not any(g.current_user.has_role(r) for r in role_names):
                return jsonify({"error": "Forbidden", "required_roles": list(role_names)}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## app/utils/response.py

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


def error_response(message="Error", status_code=400):
    return jsonify({"success": False, "message": message}), status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(e):
        return error_response(e.message, e.status_code)

    @app.errorhandler(404)
    def not_found(_):
        return error_response("Not found", 404)

    @app.errorhandler(500)
    def internal(_):
        return error_response("Internal server error", 500)
```

---

## app/services/auth_service.py

```python
import jwt as pyjwt
from datetime import datetime, timezone

from ..models.user           import User
from ..models.token_blacklist import TokenBlacklist
from ..extensions            import db
from ..utils.jwt_utils       import create_access_token, create_refresh_token, decode_token, extract_bearer
from ..utils.response        import ApiError


class AuthService:

    @staticmethod
    def register(data: dict) -> User:
        if User.query.filter_by(email=data["email"]).first():
            raise ApiError("Email already registered", 409)
        if User.query.filter_by(username=data["username"]).first():
            raise ApiError("Username already taken", 409)
        user = User(username=data["username"], email=data["email"],
                    first_name=data.get("first_name"), last_name=data.get("last_name"))
        user.password = data["password"]
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
        extra = {"username": user.username,
                 "roles": [r.name for r in user.roles],
                 "permissions": list(user.get_all_permissions())}
        return {
            "access_token":  create_access_token(user.id, extra=extra),
            "refresh_token": create_refresh_token(user.id),
            "token_type":    "Bearer",
            "user":          user.to_dict(),
        }

    @staticmethod
    def logout(auth_header: str) -> dict:
        token = extract_bearer(auth_header)
        try:
            payload  = decode_token(token)
            exp      = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            TokenBlacklist.revoke(payload["jti"], "access", exp)
        except pyjwt.PyJWTError:
            pass
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
            raise ApiError("Token has been revoked", 401)
        user = User.query.get(int(payload["sub"]))
        if not user:
            raise ApiError("User not found", 404)
        extra = {"username": user.username,
                 "roles": [r.name for r in user.roles],
                 "permissions": list(user.get_all_permissions())}
        return {"access_token": create_access_token(user.id, extra=extra), "token_type": "Bearer"}
```

---

## app/services/user_service.py

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
            q = q.filter(User.username.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
        pag = q.paginate(page=page, per_page=per_page, error_out=False)
        return {"users": [u.to_dict() for u in pag.items],
                "total": pag.total, "page": pag.page, "pages": pag.pages, "per_page": per_page}

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

---

## app/services/role_service.py

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

## app/routes/auth_routes.py

```python
from flask import Blueprint, request, g
from ..services.auth_service     import AuthService
from ..middleware.auth_middleware import jwt_required
from ..utils.response            import success_response, error_response

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

## app/routes/user_routes.py

```python
from flask import Blueprint, request, g
from ..services.user_service     import UserService
from ..middleware.auth_middleware import permission_required, role_required
from ..utils.response            import success_response

user_bp = Blueprint("users", __name__)


@user_bp.route("/", methods=["GET"])
@permission_required("users", "read")
def list_users():
    return success_response(UserService.get_all(
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 10, type=int),
        search=request.args.get("search", ""),
    ))


@user_bp.route("/<int:user_id>", methods=["GET"])
@permission_required("users", "read")
def get_user(user_id):
    return success_response(UserService.get_by_id(user_id).to_dict())


@user_bp.route("/", methods=["POST"])
@permission_required("users", "create")
def create_user():
    return success_response(UserService.create(request.get_json() or {}).to_dict(), "Created", 201)


@user_bp.route("/<int:user_id>", methods=["PUT"])
@permission_required("users", "update")
def update_user(user_id):
    return success_response(UserService.update(user_id, request.get_json() or {}).to_dict(), "Updated")


@user_bp.route("/<int:user_id>", methods=["DELETE"])
@permission_required("users", "delete")
def delete_user(user_id):
    UserService.delete(user_id)
    return success_response(None, "Deleted")


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

---

## app/routes/role_routes.py

```python
from flask import Blueprint, request
from ..services.role_service     import RoleService
from ..middleware.auth_middleware import permission_required
from ..utils.response            import success_response

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
    return success_response(RoleService.create(request.get_json() or {}).to_dict(), "Created", 201)


@role_bp.route("/<int:role_id>", methods=["PUT"])
@permission_required("roles", "update")
def update_role(role_id):
    return success_response(RoleService.update(role_id, request.get_json() or {}).to_dict(), "Updated")


@role_bp.route("/<int:role_id>", methods=["DELETE"])
@permission_required("roles", "delete")
def delete_role(role_id):
    RoleService.delete(role_id)
    return success_response(None, "Deleted")


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

---

## app/routes/permission_routes.py

```python
from flask import Blueprint, request
from ..models.permission         import Permission
from ..extensions                import db
from ..middleware.auth_middleware import permission_required
from ..utils.response            import success_response, error_response, ApiError

permission_bp = Blueprint("permissions", __name__)


@permission_bp.route("/", methods=["GET"])
@permission_required("permissions", "read")
def list_permissions():
    perms = Permission.query.all()
    return success_response([p.to_dict() for p in perms])


@permission_bp.route("/<int:perm_id>", methods=["GET"])
@permission_required("permissions", "read")
def get_permission(perm_id):
    perm = Permission.query.get(perm_id)
    if not perm:
        raise ApiError("Permission not found", 404)
    return success_response(perm.to_dict())


@permission_bp.route("/", methods=["POST"])
@permission_required("permissions", "create")
def create_permission():
    data = request.get_json() or {}
    if not all([data.get("name"), data.get("resource"), data.get("action")]):
        return error_response("name, resource, action are required", 400)
    if Permission.query.filter_by(name=data["name"]).first():
        return error_response("Permission already exists", 409)
    perm = Permission(name=data["name"], resource=data["resource"],
                      action=data["action"], description=data.get("description"))
    db.session.add(perm)
    db.session.commit()
    return success_response(perm.to_dict(), "Created", 201)


@permission_bp.route("/<int:perm_id>", methods=["PUT"])
@permission_required("permissions", "update")
def update_permission(perm_id):
    perm = Permission.query.get(perm_id)
    if not perm:
        raise ApiError("Permission not found", 404)
    data = request.get_json() or {}
    for field in ("name", "resource", "action", "description"):
        if field in data:
            setattr(perm, field, data[field])
    db.session.commit()
    return success_response(perm.to_dict(), "Updated")


@permission_bp.route("/<int:perm_id>", methods=["DELETE"])
@permission_required("permissions", "delete")
def delete_permission(perm_id):
    perm = Permission.query.get(perm_id)
    if not perm:
        raise ApiError("Permission not found", 404)
    db.session.delete(perm)
    db.session.commit()
    return success_response(None, "Deleted")
```

---

## app/routes/__init__.py

```python
# empty
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

## Database Switching (change .env only)

```env
# SQLite (quick test)
DATABASE_URL=sqlite:///dev.db

# MySQL (default)
DB_DRIVER=mysql+pymysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flask_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/flask_rbac_db
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
| GET | /api/users/ | permission:users:read |
| POST | /api/users/ | permission:users:create |
| GET | /api/users/\<id\> | permission:users:read |
| PUT | /api/users/\<id\> | permission:users:update |
| DELETE | /api/users/\<id\> | permission:users:delete |
| POST | /api/users/\<id\>/roles | role:admin |
| DELETE | /api/users/\<id\>/roles/\<rid\> | role:admin |
| GET | /api/roles/ | permission:roles:read |
| POST | /api/roles/ | permission:roles:create |
| PUT | /api/roles/\<id\> | permission:roles:update |
| DELETE | /api/roles/\<id\> | permission:roles:delete |
| POST | /api/roles/\<id\>/permissions | permission:roles:update |
| DELETE | /api/roles/\<id\>/permissions/\<pid\> | permission:roles:update |
| GET | /api/permissions/ | permission:permissions:read |
| POST | /api/permissions/ | permission:permissions:create |
| PUT | /api/permissions/\<id\> | permission:permissions:update |
| DELETE | /api/permissions/\<id\> | permission:permissions:delete |
