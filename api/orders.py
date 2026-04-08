from fastapi import APIRouter, Depends, HTTPException

from adapters.base import AdapterError
from adapters.messenger_adapter import MessengerAdapter
from adapters.table_adapter import TableAdapter
from adapters.uds_adapter import UDSAdapter
from integram.client import IntegramClient
from integram.deps import get_integram
from integram.mappers import igm_to_event, igm_to_order
from schemas.enums import OrderSource, OrderStatus
from schemas.order import (
    OrderCreate,
    OrderEventRead,
    OrderFromSource,
    OrderRead,
    OrderStatusUpdate,
)
from services.client_service import find_or_create
from services.fsm import FSMError
from services.order_service import create_order, get_history, transition_status

_ADAPTERS = {
    OrderSource.UDS: UDSAdapter(),
    OrderSource.MESSENGER: MessengerAdapter(),
    OrderSource.TABLE: TableAdapter(),
}

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderRead, status_code=201)
async def create_order_endpoint(
    data: OrderCreate, igm: IntegramClient = Depends(get_integram)
):
    if not await igm.get_object(igm.T_CLIENTS, data.client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    order = await create_order(igm, client_id=data.client_id, source=data.source, payload=data.payload)
    return igm_to_order(order)


@router.post("/from-source", response_model=OrderRead, status_code=201)
async def create_order_from_source(
    data: OrderFromSource, igm: IntegramClient = Depends(get_integram)
):
    # 1. Нормализовать raw через адаптер источника
    adapter = _ADAPTERS[data.source]
    try:
        payload = adapter.normalize(data.raw)
    except AdapterError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 2. Найти или создать клиента (дедупликация)
    client_data = data.client
    if not client_data.phone and not client_data.email:
        raise HTTPException(status_code=422, detail="Нужен хотя бы phone или email клиента")
    client, _ = await find_or_create(
        igm,
        phone=client_data.phone,
        email=client_data.email,
        name=client_data.name,
    )

    # 3. Создать заказ + OrderEvent
    order = await create_order(igm, client_id=client["id"], source=data.source, payload=payload)
    return igm_to_order(order)


@router.get("/", response_model=list[OrderRead])
async def list_orders(
    skip: int = 0, limit: int = 100, igm: IntegramClient = Depends(get_integram)
):
    rows = await igm.list_objects(igm.T_ORDERS, skip=skip, limit=limit)
    return [igm_to_order(r) for r in rows]


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, igm: IntegramClient = Depends(get_integram)):
    row = await igm.get_object(igm.T_ORDERS, order_id)
    if not row:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return igm_to_order(row)


@router.get("/{order_id}/history", response_model=list[OrderEventRead])
async def get_order_history(order_id: int, igm: IntegramClient = Depends(get_integram)):
    if not await igm.get_object(igm.T_ORDERS, order_id):
        raise HTTPException(status_code=404, detail="Заказ не найден")
    events = await get_history(igm, order_id)
    return [igm_to_event(e, order_id) for e in events]


@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: int, data: OrderStatusUpdate, igm: IntegramClient = Depends(get_integram)
):
    row = await igm.get_object(igm.T_ORDERS, order_id)
    if not row:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order_dict = igm_to_order(row)
    try:
        updated_raw = await transition_status(
            igm, order_dict, data.status, actor=data.actor, meta=data.meta
        )
    except FSMError as e:
        raise HTTPException(status_code=422, detail=str(e))
    # После update_object Integram возвращает raw dict — нужно дополнить notes из исходного
    # чтобы mapper смог извлечь source и payload
    if "notes" not in updated_raw and "notes" in row:
        updated_raw["notes"] = row["notes"]
    return igm_to_order(updated_raw)
