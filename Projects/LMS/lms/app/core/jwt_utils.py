import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from lms.app.config import settings

def create_access_token(user_id: int, expires_delta: timedelta | None = None, extra: dict = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + settings.access_token_ttl
    to_encode = {"sub": str(user_id), "exp": expire, "type": "access"}
    if extra:
        to_encode.update(extra)
    encoded_jwt = pyjwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + settings.refresh_token_ttl
    to_encode = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    encoded_jwt = pyjwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    return pyjwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

def extract_bearer(token: str) -> str:
    # This function might be used if the token comes with "Bearer " prefix
    # For HTTPBearer, it's usually just the token itself.
    if token.startswith("Bearer "):
        return token.split(" ")[1]
    return token