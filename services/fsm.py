"""FSM переходы заказа.

Допустимые переходы:
  NEW → CONFIRMED | CANCELLED
  CONFIRMED → IN_PROGRESS | CANCELLED
  IN_PROGRESS → DONE | CANCELLED
  DONE / CANCELLED — финальные, переходов нет
"""

import json
import logging

from integram.client import IntegramClient
from schemas.enums import OrderStatus

logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.NEW: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
    OrderStatus.IN_PROGRESS: {OrderStatus.DONE, OrderStatus.CANCELLED},
    OrderStatus.DONE: set(),
    OrderStatus.CANCELLED: set(),
}


class FSMError(Exception):
    pass


async def transition(
    igm: IntegramClient,
    order: dict,
    new_status: OrderStatus,
    actor: str | None = None,
    meta: dict | None = None,
) -> dict:
    """Сменить статус заказа и записать событие.

    order — dict из igm_to_order (human-readable status).
    Возвращает raw Integram dict (до маппинга).
    """
    current = OrderStatus(order["status"])
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise FSMError(
            f"Переход {current} → {new_status} недопустим. "
            f"Разрешены: {[s.value for s in allowed] or 'нет (финальный статус)'}"
        )

    if igm.T_EVENTS:
        try:
            await igm.create_object(
                igm.T_EVENTS,
                {
                    "from_status": current.value,
                    "to_status": new_status.value,
                    "actor": actor or "",
                    "meta": json.dumps(meta) if meta else "null",
                },
                parentId=order["id"],
            )
        except Exception as exc:
            logger.warning("OrderEvent failed (order %d): %s", order["id"], exc)

    status_id = igm.STATUS_MAP[new_status.value]
    return await igm.update_object(igm.T_ORDERS, order["id"], {"status": status_id})
