"""order_service.py — бизнес-логика заказов."""

from sqlalchemy.orm import Session

from models.order import Order, OrderSource, OrderStatus
from models.order_event import OrderEvent
from services.fsm import transition


def create_order(
    db: Session,
    client_id: int,
    source: OrderSource,
    payload: dict | None = None,
) -> Order:
    """Создать заказ и записать событие создания в order_events."""
    order = Order(
        client_id=client_id,
        source=source,
        status=OrderStatus.NEW,
        payload=payload or {},
    )
    db.add(order)
    db.flush()

    # Событие создания (from_status=None — начало жизни заказа)
    event = OrderEvent(
        order_id=order.id,
        from_status=None,
        to_status=OrderStatus.NEW,
        actor="system",
        meta={"source": source.value},
    )
    db.add(event)
    return order


def transition_status(
    db: Session,
    order: Order,
    new_status: OrderStatus,
    actor: str | None = None,
    meta: dict | None = None,
) -> Order:
    """Сменить статус через FSM."""
    return transition(db, order, new_status, actor=actor, meta=meta)


def get_history(db: Session, order_id: int) -> list[OrderEvent]:
    """Полная история переходов заказа."""
    return (
        db.query(OrderEvent)
        .filter(OrderEvent.order_id == order_id)
        .order_by(OrderEvent.created_at.asc())
        .all()
    )
