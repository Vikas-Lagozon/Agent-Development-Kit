from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """
    Schema for the JWT access token response.
    """
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    """
    Schema for user registration request.
    """
    username:   str      = Field(..., min_length=3, max_length=80)
    email:      EmailStr
    password:   str      = Field(..., min_length=8)
    first_name: str | None = None
    last_name:  str | None = None


class LoginRequest(BaseModel):
    """
    Schema for user login request.
    """
    email:    EmailStr
    password: str


class RefreshRequest(BaseModel):
    """
    Schema for refreshing JWT token.
    """
    refresh_token: str


class TokenResponse(BaseModel):
    """
    Schema for JWT token response.
    """
    access_token:  str
    refresh_token: str
    token_type:    str = "Bearer"


class TokenPayload(BaseModel):
    """
    Schema for JWT token payload.
    """
    username: str
