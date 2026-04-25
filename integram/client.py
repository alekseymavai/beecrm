"""integram/client.py — async HTTP клиент Integram V2 API."""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from integram.exceptions import IntegramError, IntegramNotFoundError

logger = logging.getLogger(__name__)


class IntegramClient:
    IAM  = "https://ai2o.online/api/v2/iam"

    # ── workspace: usadba ──────────────────────────────────────────────────
    T_CLIENTS  = 21
    T_ORDERS   = 24
    T_EVENTS   = 28890  # child-таблица «История изменений заказа» (parentTypeId=24)
    T_STATUSES = 15
    T_SOURCES  = 14
    T_PRODUCTS = 23

    # ── Users (таблица «Пользователи CRM», typeId 28885) ───────────────────
    T_USERS         = 28885
    COL_USER_LOGIN  = 28886  # login (text)
    COL_USER_HASH   = 28887  # password_hash (text)
    COL_USER_ROLE   = 28888  # role (text)
    COL_USER_ACTIVE = 28889  # is_active (bool)

    COL_PRODUCT_PRICE       = 47
    COL_PRODUCT_CATEGORY    = 81
    COL_PRODUCT_STOCK       = None  # usadba не ведёт остатки
    COL_PRODUCT_ACTIVE      = 54
    COL_PRODUCT_DESCRIPTION = 50

    STATUS_MAP = {
        "NEW":         130,
        "CONFIRMED":   131,
        "IN_PROGRESS": 132,
        "DONE":        134,   # usadba: «Доставлен»
        "CANCELLED":   135,
    }
    SOURCE_MAP = {
        "UDS":       122,
        "MESSENGER": 125,   # Telegram
        "TABLE":     123,   # ВК
    }

    # Col IDs — Клиенты (typeId 21)
    COL_CLIENT_NOTES = 39   # Примечание
    COL_CLIENT_PHONE = 29
    COL_CLIENT_EMAIL = 30

    # Col IDs — Заказы (typeId 24)
    COL_ORDER_CLIENT     = 83   # ref → Клиенты
    COL_ORDER_STATUS     = 87   # ref → Статусы заказа (скрыт в schema, работает)
    COL_ORDER_SOURCE     = 82   # ref → Источники
    COL_ORDER_AMOUNT     = 60   # Сумма (валюта)
    COL_ORDER_NOTES      = None # usadba: комментарии в child-таблице 27
    COL_ORDER_CREATED_AT = 56   # Дата

    # Col IDs — История изменений заказа (typeId 28890)
    COL_EVENT_FROM   = 28891  # Предыдущий статус
    COL_EVENT_TO     = 28892  # Новый статус
    COL_EVENT_ACTOR  = 28893  # Кто изменил
    COL_EVENT_META   = 28894  # Описание
    COL_EVENT_TIME   = 28895  # Дата изменения

    def __init__(self, login: str, password: str, token: str | None = None, workspace: str = "usadba") -> None:
        self._login    = login
        self._password = password
        self._token    = token
        self._http     = httpx.AsyncClient(timeout=30.0)
        self.BASE      = f"https://ai2o.online/api/v2/{workspace}"

    @classmethod
    async def authenticate(cls, login: str, password: str, workspace: str = "usadba") -> "IntegramClient":
        instance = cls(login, password, workspace=workspace)
        await instance._refresh_token()
        return instance

    async def _refresh_token(self) -> None:
        resp = await self._http.post(
            f"{self.IAM}/login",
            json={"email": self._login, "password": self._password},
        )
        if not resp.is_success:
            raise IntegramError(f"Auth failed: {resp.status_code} {resp.text}")
        self._token = resp.json()["accessToken"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        resp = await self._http.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 401:
            await self._refresh_token()
            resp = await self._http.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 404:
            raise IntegramNotFoundError(url)
        if not resp.is_success:
            raise IntegramError(f"{method} {url} → {resp.status_code}: {resp.text}")
        data = resp.json()
        return data.get("data", data) if isinstance(data, dict) and "data" in data else data

    # ── Objects ───────────────────────────────────────────────────────────────

    async def list_objects(
        self,
        typeId: int,
        page: int = 1,
        page_size: int = 50,
        parent_id: int | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {"typeId": typeId, "page": page, "pageSize": page_size}
        if parent_id is not None:
            params["parentId"] = parent_id
        data = await self._request("GET", f"{self.BASE}/objects", params=params)
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("rows", data.get("items", data.get("data", [])))
        else:
            rows = []
        # Integram V2 list API returns sparse rows (no requisites).
        # Enrich concurrently for tables whose mappers need requisites.
        if rows and typeId in {self.T_ORDERS, self.T_CLIENTS, self.T_PRODUCTS, self.T_EVENTS}:
            tasks = [self.get_object(r["id"]) for r in rows]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            rows = [
                full if isinstance(full, dict) else orig
                for orig, full in zip(rows, results)
            ]
        return rows

    async def get_object(self, objId: int) -> dict | None:
        try:
            return await self._request("GET", f"{self.BASE}/objects/{objId}")
        except IntegramNotFoundError:
            return None

    async def create_object(
        self,
        typeId: int,
        value: str = "",
        requisites: dict[str, Any] | None = None,
        parentId: int = 1,
    ) -> dict:
        body: dict[str, Any] = {"typeId": typeId, "parentId": parentId, "value": value}
        if requisites:
            body["requisites"] = requisites
        return await self._request("POST", f"{self.BASE}/objects", json=body)

    async def update_object(
        self,
        objId: int,
        value: str | None = None,
        requisites: dict[str, Any] | None = None,
    ) -> dict:
        body: dict[str, Any] = {}
        if value is not None:
            body["value"] = value
        if requisites:
            body["requisites"] = requisites
        return await self._request("PATCH", f"{self.BASE}/objects/{objId}", json=body)

    async def find_by_field(self, typeId: int, col_id: int, value: str) -> dict | None:
        """Поиск объекта по значению колонки (для дедупликации клиентов)."""
        try:
            data = await self._request(
                "GET",
                f"{self.BASE}/objects",
                params={
                    "typeId": typeId,
                    "pageSize": 1,
                    f"filter[{col_id}][eq]": value,
                },
            )
            rows = data.get("rows", []) if isinstance(data, dict) else data
            return rows[0] if rows else None
        except (IntegramNotFoundError, IntegramError):
            return None

    async def find_user_by_login(self, login: str) -> dict | None:
        """Поиск пользователя в T_USERS по логину (client-side, т.к. V2 не фильтрует по реквизитам).

        Получаем все записи таблицы T_USERS (их обычно мало),
        для каждой загружаем полный объект с реквизитами и сравниваем COL_USER_LOGIN.
        """
        try:
            rows = await self.list_objects(self.T_USERS, page_size=200)
        except (IntegramNotFoundError, IntegramError):
            return None
        for row in rows:
            obj = await self.get_object(row["id"])
            if obj is None:
                continue
            reqs = obj.get("requisites") or {}
            if str(reqs.get(str(self.COL_USER_LOGIN), "")) == str(login):
                return obj
        return None

    async def list_children(self, child_typeId: int, parent_id: int) -> list[dict]:
        """Child-записи для конкретного объекта."""
        return await self.list_objects(child_typeId, parent_id=parent_id, page_size=200)

    async def list_orders_by_client(self, client_id: int) -> list[dict]:
        """Все заказы клиента — серверная фильтрация + пагинация."""
        result = []
        page = 1
        while True:
            data = await self._request(
                "GET",
                f"{self.BASE}/objects",
                params={
                    "typeId": self.T_ORDERS,
                    "page": page,
                    "pageSize": 100,
                    f"filter[{self.COL_ORDER_CLIENT}][eq]": str(client_id),
                },
            )
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = data.get("rows", data.get("items", data.get("data", [])))
            else:
                rows = []
            # Enrich sparse rows with full requisites
            tasks = [self.get_object(r["id"]) for r in rows]
            full_rows = await asyncio.gather(*tasks, return_exceptions=True)
            enriched = [
                full if isinstance(full, dict) else orig
                for orig, full in zip(rows, full_rows)
            ]
            result.extend(enriched)
            if len(rows) < 100:
                break
            page += 1
        return result

    # ── Orders ────────────────────────────────────────────────────────────────

    async def create_order_with_event(
        self,
        client_id: int,
        status_id: int,
        source: str,
        payload: dict,
        actor: str = "system",
    ) -> dict:
        reqs: dict[str, Any] = {
            str(self.COL_ORDER_CLIENT): client_id,
            str(self.COL_ORDER_STATUS): status_id,
            str(self.COL_ORDER_SOURCE): self.SOURCE_MAP.get(source, 0),
        }
        if self.COL_ORDER_NOTES is not None:
            notes = json.dumps({"source": source, "payload": payload}, ensure_ascii=False)
            reqs[str(self.COL_ORDER_NOTES)] = notes
        order = await self.create_object(
            self.T_ORDERS,
            value="",
            requisites=reqs,
        )
        order_id = order["id"]

        if self.T_EVENTS:
            try:
                await self.create_object(
                    self.T_EVENTS,
                    value="",
                    requisites={
                        str(self.COL_EVENT_FROM):  "",
                        str(self.COL_EVENT_TO):    "NEW",
                        str(self.COL_EVENT_ACTOR): actor,
                        str(self.COL_EVENT_META):  json.dumps({"source": source}),
                    },
                    parentId=order_id,
                )
            except Exception as exc:
                logger.warning("OrderEvent creation failed (order %d): %s", order_id, exc)

        return order

    # ── Import ────────────────────────────────────────────────────────────────

    async def import_preview(self, file_bytes: bytes, filename: str) -> dict:
        resp = await self._http.post(
            f"{self.BASE}/objects/import/preview",
            headers=self._headers(),
            files={"file": (filename, file_bytes)},
        )
        if resp.status_code == 401:
            await self._refresh_token()
            resp = await self._http.post(
                f"{self.BASE}/objects/import/preview",
                headers=self._headers(),
                files={"file": (filename, file_bytes)},
            )
        if not resp.is_success:
            raise IntegramError(f"import/preview → {resp.status_code}: {resp.text}")
        data = resp.json()
        return data.get("data", data)

    async def import_xlsx(
        self,
        file_bytes: bytes,
        filename: str,
        typeId: int,
        mapping: dict[str, str] | None = None,
    ) -> dict:
        form: dict[str, Any] = {"typeId": str(typeId)}
        if mapping:
            form["mapping"] = json.dumps(mapping)
        resp = await self._http.post(
            f"{self.BASE}/objects/import",
            headers=self._headers(),
            files={"file": (filename, file_bytes)},
            data=form,
            timeout=60.0,
        )
        if resp.status_code == 401:
            await self._refresh_token()
            resp = await self._http.post(
                f"{self.BASE}/objects/import",
                headers=self._headers(),
                files={"file": (filename, file_bytes)},
                data=form,
                timeout=60.0,
            )
        if not resp.is_success:
            raise IntegramError(f"import → {resp.status_code}: {resp.text}")
        data = resp.json()
        return data.get("data", data)

    async def close(self) -> None:
        await self._http.aclose()


# ── V2 API alias-format normalization ─────────────────────────────────────────
# Integram list_objects returns alias-keys (column names) without a requisites dict.
# Mappers expect {requisites: {str(colId): value}}.
# _normalize_alias_row() converts transparently; no-op if requisites already present.

_REF_SUFFIX_RE = re.compile(r'\(id:(\d+)\)\s*$')
_REF_NAME_RE   = re.compile(r'^(.*?)\s*\(id:\d+\)\s*$')
_NUM_PREFIX_RE = re.compile(r'^(-?\d+(?:\.\d+)?)\b')


def _alias_ref_id(value: str | None) -> str | None:
    """'Название (id:123)' → '123'  (anchored at right to avoid false matches)."""
    if not value:
        return None
    m = _REF_SUFFIX_RE.search(str(value))
    return m.group(1) if m else None


def _alias_ref_name(value: str | None) -> str | None:
    """'Название (id:123)' → 'Название'."""
    if not value:
        return None
    m = _REF_NAME_RE.match(str(value))
    return m.group(1).strip() if m else str(value)


def _alias_num(value: str | None) -> str | None:
    """'78 (id:1300)' → '78';  '350.50' → '350.50'."""
    if value is None:
        return None
    m = _NUM_PREFIX_RE.match(str(value))
    return m.group(1) if m else (str(value) if value else None)


def _unix_to_iso(ts: str | None) -> str | None:
    """Unix timestamp string → UTC ISO-8601 string (timezone-safe)."""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (ValueError, TypeError, OSError):
        return str(ts)


# alias → (colId_str, field_type) per typeId.
# field_type: "ref" | "ref_name" | "num" | "date" | "bool" | "text"
_ALIAS_MAPS: dict[int, dict[str, tuple[str, str]]] = {
    IntegramClient.T_CLIENTS: {
        "Телефон": (str(IntegramClient.COL_CLIENT_PHONE), "text"),
        "Email":   (str(IntegramClient.COL_CLIENT_EMAIL),  "text"),
    },
    IntegramClient.T_ORDERS: {
        "Статус заказа": (str(IntegramClient.COL_ORDER_STATUS),     "ref"),
        "Источник":      (str(IntegramClient.COL_ORDER_SOURCE),     "ref"),
        "Клиент":        (str(IntegramClient.COL_ORDER_CLIENT),     "ref"),
        "Дата":          (str(IntegramClient.COL_ORDER_CREATED_AT), "date"),
        "Сумма":         (str(IntegramClient.COL_ORDER_AMOUNT),     "num"),
    },
    IntegramClient.T_PRODUCTS: {
        "Цена":      (str(IntegramClient.COL_PRODUCT_PRICE),        "num"),
        "Категория": (str(IntegramClient.COL_PRODUCT_CATEGORY),     "ref_name"),
        "В наличии": (str(IntegramClient.COL_PRODUCT_ACTIVE),       "bool"),
        "Описание":  (str(IntegramClient.COL_PRODUCT_DESCRIPTION),  "text"),
    },
}


def _normalize_alias_row(typeId: int, row: dict) -> dict:
    """Convert Integram V2 list alias-format row to requisites-format for mappers.

    list_objects returns alias-keys (column names) without a requisites dict.
    get_object / create_object / FakeIntegramClient already return requisites-format
    and are returned unchanged.
    """
    if "requisites" in row:
        return row

    alias_map = _ALIAS_MAPS.get(typeId, {})
    requisites: dict[str, Any] = {}

    for alias, (col_id, field_type) in alias_map.items():
        raw = row.get(alias)
        if raw is None:
            continue
        if field_type == "ref":
            val = _alias_ref_id(raw)
            if val is not None:
                requisites[col_id] = val
        elif field_type == "ref_name":
            val = _alias_ref_name(raw)
            if val is not None:
                requisites[col_id] = val
        elif field_type == "num":
            val = _alias_num(raw)
            if val is not None:
                requisites[col_id] = val
        elif field_type == "date":
            val = _unix_to_iso(str(raw))
            if val is not None:
                requisites[col_id] = val
        elif field_type == "bool":
            requisites[col_id] = raw
        else:  # "text"
            requisites[col_id] = raw

    normalized: dict[str, Any] = {
        **row,
        "value": row.get("name") or row.get("value") or "",
        "requisites": requisites,
    }

    # Inject createdAt from unix date aliases for mappers that read row["createdAt"]
    if not normalized.get("createdAt") and typeId == IntegramClient.T_CLIENTS:
        raw_date = row.get("Дата регистрации")
        if raw_date:
            normalized["createdAt"] = _unix_to_iso(str(raw_date))

    return normalized
