from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class ClientCreate(BaseModel):
    phone: str | None = None
    email: EmailStr | None = None
    name: str | None = None

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 32:
            raise ValueError("phone слишком длинный")
        return v

    def model_post_init(self, __context) -> None:
        if not self.phone and not self.email:
            raise ValueError("Нужен хотя бы phone или email")


class ClientRead(BaseModel):
    id: int
    phone: str | None
    email: str | None
    name: str | None
    created_at: datetime
    updated_at: datetime


class ClientUpdate(BaseModel):
    phone: str | None = None
    email: EmailStr | None = None
    name: str | None = None
