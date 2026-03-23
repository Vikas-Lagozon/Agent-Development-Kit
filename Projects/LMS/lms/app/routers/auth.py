import jwt as pyjwt
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from lms.app.database.session import get_db
from lms.app.models.user         import User
from lms.app.schemas.auth        import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest
from lms.app.core.jwt_utils      import (
    create_access_token, create_refresh_token,
    decode_token, extract_bearer
)
from lms.app.core.dependencies   import get_current_user

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
    }
    access_token  = create_access_token(user.id, extra=extra)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
    )


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

    result = await db.execute(select(User).where(User.id == int(token_data["sub"])))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    extra = {
        "username":    user.username,
    }
    return {"success": True, "data": {"access_token": create_access_token(user.id, extra=extra), "token_type": "Bearer"}}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "id":          current_user.id,
            "username":    current_user.username,
            "email":       current_user.email,
        },
    }