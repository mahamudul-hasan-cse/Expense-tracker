from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be blank")
        return v


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    icon: Optional[str]
    is_default: bool

    class Config:
        from_attributes = True


class CategoriesListResponse(BaseModel):
    categories: list[CategoryResponse]
