"""FSM переходы заказа.

Допустимые переходы:
  NEW → CONFIRMED | CANCELLED
  CONFIRMED → IN_PROGRESS | CANCELLED
  IN_PROGRESS → DONE | CANCELLED
  DONE / CANCELLED — финальные, переходов нет
"""

from sqlalchemy.orm import Session

from models.order import Order, OrderStatus
from models.order_event import OrderEvent

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.NEW: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
    OrderStatus.IN_PROGRESS: {OrderStatus.DONE, OrderStatus.CANCELLED},
    OrderStatus.DONE: set(),
    OrderStatus.CANCELLED: set(),
}


class FSMError(Exception):
    pass


def transition(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    actor: str | None = None,
    meta: dict | None = None,
) -> Order:
    """Сменить статус заказа и записать событие в order_events."""
    allowed = ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise FSMError(
            f"Переход {order.status} → {new_status} недопустим. "
            f"Разрешены: {[s.value for s in allowed] or 'нет (финальный статус)'}"
        )

    event = OrderEvent(
        order_id=order.id,
        from_status=order.status,
        to_status=new_status,
        actor=actor,
        meta=meta,
    )
    db.add(event)

    order.status = new_status
    return order
