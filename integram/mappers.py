"""integram/mappers.py — конвертация Integram dict-ответов в Pydantic-совместимые dict."""

import json
from datetime import datetime, timezone

from integram.client import IntegramClient

_REVERSE_STATUS: dict[int, str] = {v: k for k, v in IntegramClient.STATUS_MAP.items()}


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

    notes_str = req.get(str(IntegramClient.COL_ORDER_NOTES)) or "{}"
    try:
        notes = json.loads(notes_str)
    except (json.JSONDecodeError, TypeError):
        notes = {}

    status_raw = req.get(str(IntegramClient.COL_ORDER_STATUS))
    status_ref = int(status_raw) if status_raw is not None and status_raw != "" else None
    status_str = _REVERSE_STATUS.get(status_ref, "NEW") if status_ref else "NEW"

    client_raw = req.get(str(IntegramClient.COL_ORDER_CLIENT))
    client_id = int(client_raw) if client_raw else _extract_ref(row.get("client"))

    created_at = (
        req.get(str(IntegramClient.COL_ORDER_CREATED_AT))
        or row.get("createdAt")
        or row.get("created_at")
        or _now_iso()
    )
    return {
        "id": row["id"],
        "client_id": client_id,
        "source": notes.get("source", "MESSENGER"),
        "status": status_str,
        "payload": notes.get("payload", {}),
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
