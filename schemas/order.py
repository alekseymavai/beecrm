from datetime import datetime

from pydantic import BaseModel, field_validator

from models.order import OrderSource, OrderStatus


class OrderCreate(BaseModel):
    client_id: int
    source: OrderSource
    payload: dict = {}

    @field_validator("payload")
    @classmethod
    def payload_size(cls, v: dict) -> dict:
        import json
        from settings import MAX_PAYLOAD_BYTES
        if len(json.dumps(v).encode()) > MAX_PAYLOAD_BYTES:
            raise ValueError(f"payload превышает {MAX_PAYLOAD_BYTES} байт")
        return v


class OrderRead(BaseModel):
    id: int
    client_id: int
    source: OrderSource
    status: OrderStatus
    payload: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    actor: str | None = None
    meta: dict | None = None


class OrderEventRead(BaseModel):
    id: int
    order_id: int
    from_status: OrderStatus | None
    to_status: OrderStatus
    actor: str | None
    meta: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
