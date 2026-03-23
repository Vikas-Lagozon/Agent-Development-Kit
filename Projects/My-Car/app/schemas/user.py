from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


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
    created_at:  datetime
    last_login:  datetime | None

    model_config = {"from_attributes": True}
