from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    icon: Optional[str]
    is_default: bool

    class Config:
        from_attributes = True


class CategoriesListResponse(BaseModel):
    categories: list[CategoryResponse]
