from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import jwt, JWTError
from pydantic import ValidationError

from app.database.base import get_db
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.config import settings

# This URL should match the endpoint that provides the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decodes the JWT token to get the current user.

    - Raises HTTPException 401 for any token validation errors.
    - Fetches and returns the user from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # The 'sub' (subject) of the token is expected to be the username
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Validate payload structure
        token_data = TokenPayload(username=username)

    except (JWTError, ValidationError):
        raise credentials_exception

    # Fetch user from the database
    result = await db.execute(select(User).where(User.username == token_data.username))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user
