"""integram/mappers.py — конвертация Integram dict-ответов в Pydantic-совместимые dict."""

import json
from datetime import datetime, timezone

from integram.client import IntegramClient

_REVERSE_STATUS: dict[int, str] = {v: k for k, v in IntegramClient.STATUS_MAP.items()}
_REVERSE_SOURCE: dict[int, str] = {v: k for k, v in IntegramClient.SOURCE_MAP.items()}


def _extract_ref(value: int | dict | None) -> int | None:
    if isinstance(value, dict):
        return value.get("id")
    return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def igm_to_client(row: dict) -> dict:
    req = row.get("requisites") or {}
    created_at = row.get("createdAt") or row.get("created_at") or _now_iso()
    phone = req.get(str(IntegramClient.COL_CLIENT_PHONE)) or None
    email = req.get(str(IntegramClient.COL_CLIENT_EMAIL)) or None
    return {
        "id": row["id"],
        "name": row.get("value") or None,
        "phone": phone,
        "email": email,
        "created_at": created_at,
        "updated_at": row.get("updatedAt") or row.get("updated_at") or created_at,
    }


def igm_to_order(row: dict) -> dict:
    req = row.get("requisites") or {}

    if IntegramClient.COL_ORDER_NOTES is not None:
        notes_str = req.get(str(IntegramClient.COL_ORDER_NOTES)) or "{}"
    else:
        notes_str = "{}"
    try:
        notes = json.loads(notes_str)
    except (json.JSONDecodeError, TypeError):
        notes = {}

    status_raw = req.get(str(IntegramClient.COL_ORDER_STATUS))
    status_ref = int(status_raw) if status_raw is not None and status_raw != "" else None
    status_str = _REVERSE_STATUS.get(status_ref, "NEW") if status_ref else "NEW"

    client_raw = req.get(str(IntegramClient.COL_ORDER_CLIENT))
    client_id = int(client_raw) if client_raw else _extract_ref(row.get("client"))

    source_raw_ref = req.get(str(IntegramClient.COL_ORDER_SOURCE))
    source_from_ref = _REVERSE_SOURCE.get(int(source_raw_ref)) if source_raw_ref else None

    created_at = (
        req.get(str(IntegramClient.COL_ORDER_CREATED_AT))
        or row.get("createdAt")
        or row.get("created_at")
        or _now_iso()
    )
    return {
        "id": row["id"],
        "client_id": client_id,
        "source": notes.get("source") or source_from_ref or "MESSENGER",
        "status": status_str,
        "payload": notes.get("payload", {}),
        "created_at": created_at,
        "updated_at": row.get("updatedAt") or row.get("updated_at") or created_at,
    }


def igm_to_product(row: dict) -> dict:
    req = row.get("requisites") or {}
    created_at = row.get("createdAt") or row.get("created_at") or _now_iso()
    price_raw = req.get(str(IntegramClient.COL_PRODUCT_PRICE))
    stock_raw = req.get(str(IntegramClient.COL_PRODUCT_STOCK)) if IntegramClient.COL_PRODUCT_STOCK is not None else None
    active_raw = req.get(str(IntegramClient.COL_PRODUCT_ACTIVE))
    return {
        "id": row["id"],
        "name": row.get("value") or "",
        "price": float(price_raw) if price_raw not in (None, "") else 0.0,
        "category": req.get(str(IntegramClient.COL_PRODUCT_CATEGORY)) or "",
        "stock": int(float(stock_raw)) if stock_raw not in (None, "") else 0,
        "active": bool(active_raw) if active_raw is not None else True,
        "description": req.get(str(IntegramClient.COL_PRODUCT_DESCRIPTION)) or "",
        "created_at": created_at,
        "updated_at": row.get("updatedAt") or row.get("updated_at") or created_at,
    }


def igm_to_event(row: dict, order_id: int) -> dict:
    req = row.get("requisites") or {}

    meta_str = req.get(str(IntegramClient.COL_EVENT_META)) or "null"
    try:
        meta = json.loads(meta_str)
    except (json.JSONDecodeError, TypeError):
        meta = None

    from_status = req.get(str(IntegramClient.COL_EVENT_FROM)) or None
    if from_status == "":
        from_status = None

    return {
        "id": row["id"],
        "order_id": order_id,
        "from_status": from_status,
        "to_status": req.get(str(IntegramClient.COL_EVENT_TO), "NEW"),
        "actor": req.get(str(IntegramClient.COL_EVENT_ACTOR)) or None,
        "meta": meta,
        "created_at": (
            req.get(str(IntegramClient.COL_EVENT_TIME))
            or row.get("createdAt")
            or row.get("created_at")
            or _now_iso()
        ),
    }
