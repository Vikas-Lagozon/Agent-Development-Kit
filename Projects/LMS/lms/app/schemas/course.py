from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CourseCreate(BaseModel):
    name:        str
    description: Optional[str] = None


class CourseUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None
    is_active:   Optional[bool] = None


class CourseResponse(BaseModel):
    id:          int
    name:        str
    description: Optional[str]
    is_active:   bool
    created_at:  datetime

    model_config = {"from_attributes": True}