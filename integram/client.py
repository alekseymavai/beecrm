"""integram/client.py — async HTTP клиент Integram API с JWT аутентификацией."""

import json
import logging
from typing import Any

import httpx

from integram.exceptions import IntegramError, IntegramNotFoundError

logger = logging.getLogger(__name__)


class IntegramClient:
    BASE = "https://ai2o.online/api/v2/beecrm"

    T_CLIENTS = 16
    T_ORDERS = 17
    T_EVENTS = 37  # child-таблица "История заказов" (parentTypeId=17)
    T_STATUSES = 14
    T_SOURCES = 15

    STATUS_MAP = {
        "NEW": 18,
        "CONFIRMED": 36,
        "IN_PROGRESS": 19,
        "DONE": 20,
        "CANCELLED": 21,
    }
    SOURCE_MAP = {
        "UDS": 22,
        "MESSENGER": 23,
        "TABLE": 25,
    }

    # Col IDs (используются в search filters)
    COL_CLIENT_NOTES = 27
    COL_CLIENT_PHONE = 28
    COL_CLIENT_EMAIL = 29
    COL_ORDER_CLIENT = 30
    COL_ORDER_STATUS = 31
    COL_ORDER_AMOUNT = 33
    COL_ORDER_NOTES = 34   # JSON: {"source": "...", "payload": {...}}
    COL_ORDER_CREATED_AT = 35

    def __init__(self, login: str, password: str, token: str | None = None) -> None:
        self._login = login
        self._password = password
        self._token = token
        self._http = httpx.AsyncClient(timeout=30.0)

    @classmethod
    async def authenticate(cls, login: str, password: str) -> "IntegramClient":
        instance = cls(login, password)
        await instance._refresh_token()
        return instance

    async def _refresh_token(self) -> None:
        resp = await self._http.post(
            f"{self.BASE}/auth",
            json={"login": self._login, "password": self._password},
        )
        if not resp.is_success:
            raise IntegramError(f"Auth failed: {resp.status_code} {resp.text}")
        self._token = resp.json()["token"]

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
        return resp.json()

    async def get_object(self, typeId: int, objId: int) -> dict | None:
        try:
            return await self._request("GET", f"{self.BASE}/objects/{typeId}/{objId}")
        except IntegramNotFoundError:
            return None

    async def list_objects(self, typeId: int, skip: int = 0, limit: int = 20) -> list[dict]:
        data = await self._request(
            "GET",
            f"{self.BASE}/objects/{typeId}",
            params={"skip": skip, "limit": limit},
        )
        return data.get("rows", data) if isinstance(data, dict) else data

    async def list_children(
        self, parent_typeId: int, parent_id: int, child_typeId: int
    ) -> list[dict]:
        """Получить child-записи для конкретного объекта (child-таблицы)."""
        data = await self._request(
            "GET",
            f"{self.BASE}/objects/{child_typeId}",
            params={"parentId": parent_id},
        )
        return data.get("rows", data) if isinstance(data, dict) else data

    async def create_object(
        self, typeId: int, fields: dict, parentId: int | None = None
    ) -> dict:
        body: dict[str, Any] = {"fields": fields}
        if parentId is not None:
            body["parentId"] = parentId
        return await self._request("POST", f"{self.BASE}/objects/{typeId}", json=body)

    async def update_object(self, typeId: int, objId: int, fields: dict) -> dict:
        return await self._request(
            "PATCH",
            f"{self.BASE}/objects/{typeId}/{objId}",
            json={"fields": fields},
        )

    async def find_by_field(self, typeId: int, col_id: int, value: str) -> dict | None:
        """Найти первый объект по значению колонки (для дедупликации)."""
        try:
            data = await self._request(
                "POST",
                f"{self.BASE}/search/{typeId}",
                json={"filters": [{"colId": col_id, "value": value}]},
            )
            rows = data.get("rows", []) if isinstance(data, dict) else data
            return rows[0] if rows else None
        except IntegramNotFoundError:
            return None

    async def create_order_with_event(
        self,
        client_id: int,
        status_id: int,
        source: str,
        payload: dict,
        actor: str = "system",
    ) -> dict:
        """Создать заказ и опционально залогировать событие создания."""
        notes = json.dumps({"source": source, "payload": payload}, ensure_ascii=False)
        fields: dict[str, Any] = {
            "client": client_id,
            "status": status_id,
            "notes": notes,
        }
        order = await self.create_object(self.T_ORDERS, fields)
        order_id = order["id"]

        if self.T_EVENTS:
            try:
                await self.create_object(
                    self.T_EVENTS,
                    {
                        "from_status": "",
                        "to_status": "NEW",
                        "actor": actor,
                        "meta": json.dumps({"source": source}),
                    },
                    parentId=order_id,
                )
            except Exception as exc:
                logger.warning("OrderEvent creation failed (order %d): %s", order_id, exc)

        return order

    async def close(self) -> None:
        await self._http.aclose()
