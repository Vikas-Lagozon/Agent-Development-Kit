from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CarCreate(BaseModel):
    make:        str
    model:       str
    year:        int
    price:       float
    description: Optional[str] = None


class CarUpdate(BaseModel):
    make:        Optional[str] = None
    model:       Optional[str] = None
    year:        Optional[int] = None
    price:       Optional[float] = None
    description: Optional[str] = None
    is_available:Optional[bool] = None


class CarResponse(BaseModel):
    id:          int
    owner_id:    int
    make:        str
    model:       str
    year:        int
    price:       float
    description: Optional[str]
    is_available: bool
    created_at:  datetime

    model_config = {"from_attributes": True}
