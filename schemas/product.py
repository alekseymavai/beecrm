from typing import Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    price: float = Field(0.0, ge=0)
    category: str = ""
    stock: int = Field(0, ge=0)
    active: bool = True
    description: str = ""


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    price: Optional[float] = Field(None, ge=0)
    category: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)
    active: Optional[bool] = None
    description: Optional[str] = None


class ProductRead(BaseModel):
    id: int
    name: str
    price: float
    category: str
    stock: int
    active: bool
    description: str
    created_at: str
    updated_at: str
