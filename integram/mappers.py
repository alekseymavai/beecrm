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
    created_at = row.get("created_at") or _now_iso()
    return {
        "id": row["id"],
        "name": row.get("name"),
        "phone": row.get("phone"),
        "email": row.get("email"),
        "created_at": created_at,
        "updated_at": created_at,
    }


def igm_to_order(row: dict) -> dict:
    notes_str = row.get("notes") or "{}"
    try:
        notes = json.loads(notes_str)
    except (json.JSONDecodeError, TypeError):
        notes = {}

    status_ref = _extract_ref(row.get("status"))
    status_str = _REVERSE_STATUS.get(status_ref, "NEW") if status_ref else "NEW"

    created_at = row.get("created_at") or _now_iso()
    return {
        "id": row["id"],
        "client_id": _extract_ref(row.get("client")),
        "source": notes.get("source", "MESSENGER"),
        "status": status_str,
        "payload": notes.get("payload", {}),
        "created_at": created_at,
        "updated_at": created_at,
    }


def igm_to_event(row: dict, order_id: int) -> dict:
    meta_str = row.get("meta") or "null"
    try:
        meta = json.loads(meta_str)
    except (json.JSONDecodeError, TypeError):
        meta = None

    from_status = row.get("from_status") or None
    if from_status == "":
        from_status = None

    return {
        "id": row["id"],
        "order_id": order_id,
        "from_status": from_status,
        "to_status": row.get("to_status", "NEW"),
        "actor": row.get("actor") or None,
        "meta": meta,
        "created_at": row.get("created_at") or _now_iso(),
    }
