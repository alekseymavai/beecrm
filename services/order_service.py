"""order_service.py — бизнес-логика заказов."""

from integram.client import IntegramClient
from schemas.enums import OrderSource, OrderStatus
from services.fsm import FSMError, transition


async def create_order(
    igm: IntegramClient,
    client_id: int,
    source: OrderSource,
    payload: dict | None = None,
) -> dict:
    """Создать заказ и записать событие создания."""
    status_id = igm.STATUS_MAP[OrderStatus.NEW.value]
    return await igm.create_order_with_event(
        client_id=client_id,
        status_id=status_id,
        source=source.value,
        payload=payload or {},
        actor="system",
    )


async def transition_status(
    igm: IntegramClient,
    order: dict,
    new_status: OrderStatus,
    actor: str | None = None,
    meta: dict | None = None,
) -> dict:
    """Сменить статус через FSM. Принимает mapped dict, возвращает raw Integram dict."""
    return await transition(igm, order, new_status, actor=actor, meta=meta)


async def get_history(igm: IntegramClient, order_id: int) -> list[dict]:
    """Полная история переходов заказа (child-записи OrderEvent)."""
    if not igm.T_EVENTS:
        return []
    return await igm.list_children(igm.T_ORDERS, order_id, igm.T_EVENTS)
