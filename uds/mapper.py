"""uds/mapper.py — маппинг UDS order detail → внутренний формат BEECRM."""

from schemas.enums import OrderStatus

UDS_STATUS_MAP: dict[str, OrderStatus] = {
    "NEW": OrderStatus.NEW,
    "NEED_ACK": OrderStatus.NEW,
    "WAITING_PAYMENT": OrderStatus.NEW,
    "ACCEPTED": OrderStatus.CONFIRMED,
    "COMPLETED": OrderStatus.COMPLETED,
    "CANCELLED": OrderStatus.CANCELLED,
}


def parse_order(detail: dict) -> dict:
    """Преобразовать UDS order detail в нормализованный словарь BEECRM.

    Все поля safe: не бросает KeyError, использует .get() с дефолтами.
    """
    purchase = detail.get("purchase") or {}
    delivery = detail.get("deliveryData") or {}
    customer = detail.get("customer") or {}
    delivery_case = delivery.get("deliveryCase") or {}

    total: float = float(purchase.get("total") or 0)
    extras = purchase.get("extras") or {}
    delivery_cost: float = float(extras.get("delivery") or 0)
    items_total: float = total - delivery_cost

    customer_name: str = (
        delivery.get("receiverName")
        or customer.get("displayName")
        or ""
    )
    customer_phone: str = (
        delivery.get("receiverPhone")
        or customer.get("phone")
        or ""
    )

    goods = detail.get("goods") or {}
    raw_items = goods.get("rows") or []
    items = [
        {
            "name": str(row.get("name") or ""),
            "qty": int(row.get("qty") or 0),
            "price": float(row.get("price") or 0),
            "uds_product_id": int(row.get("id") or 0),
        }
        for row in raw_items
        if (row.get("type") or "") != "OPTION"
    ]

    return {
        "uds_order_id": int(detail.get("id") or 0),
        "state": str(detail.get("state") or ""),
        "payment_status": str(detail.get("paymentStatus") or ""),
        "date_created": str(detail.get("dateCreated") or ""),
        "total": total,
        "delivery_cost": delivery_cost,
        "items_total": items_total,
        "delivery_name": str(delivery_case.get("name") or ""),
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "address": str(delivery.get("address") or ""),
        "comment": str(delivery.get("userComment") or ""),
        "items": items,
    }
