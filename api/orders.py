from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_session
from models.client import Client
from models.order import Order
from schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from services.fsm import FSMError, transition

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderRead, status_code=201)
def create_order(data: OrderCreate, db: Session = Depends(get_session)):
    if not db.get(Client, data.client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    order = Order(**data.model_dump())
    db.add(order)
    db.flush()
    db.refresh(order)
    return order


@router.get("/", response_model=list[OrderRead])
def list_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    return db.query(Order).offset(skip).limit(limit).all()


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: Session = Depends(get_session)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_session)
):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    try:
        transition(db, order, data.status, actor=data.actor, meta=data.meta)
    except FSMError as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.flush()
    db.refresh(order)
    return order
