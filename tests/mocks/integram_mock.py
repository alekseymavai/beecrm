"""FakeIntegramClient — in-memory имитация Integram для тестов."""

import json
from typing import Any

from integram.client import IntegramClient
from integram.exceptions import IntegramError

# Константы берём из IntegramClient — mappers читают оттуда же
_C = IntegramClient


class FakeIntegramClient:
    """In-memory реализация IntegramClient. Не делает HTTP-запросов."""

    T_CLIENTS  = _C.T_CLIENTS
    T_ORDERS   = _C.T_ORDERS
    T_EVENTS   = _C.T_EVENTS
    T_STATUSES = _C.T_STATUSES
    T_SOURCES  = _C.T_SOURCES
    T_PRODUCTS = _C.T_PRODUCTS

    T_USERS         = _C.T_USERS
    COL_USER_LOGIN  = _C.COL_USER_LOGIN
    COL_USER_HASH   = _C.COL_USER_HASH
    COL_USER_ROLE   = _C.COL_USER_ROLE
    COL_USER_ACTIVE = _C.COL_USER_ACTIVE

    COL_PRODUCT_PRICE       = _C.COL_PRODUCT_PRICE
    COL_PRODUCT_CATEGORY    = _C.COL_PRODUCT_CATEGORY
    COL_PRODUCT_STOCK       = _C.COL_PRODUCT_STOCK
    COL_PRODUCT_ACTIVE      = _C.COL_PRODUCT_ACTIVE
    COL_PRODUCT_DESCRIPTION = _C.COL_PRODUCT_DESCRIPTION

    STATUS_MAP = _C.STATUS_MAP
    SOURCE_MAP = _C.SOURCE_MAP

    COL_CLIENT_NOTES     = _C.COL_CLIENT_NOTES
    COL_CLIENT_PHONE     = _C.COL_CLIENT_PHONE
    COL_CLIENT_EMAIL     = _C.COL_CLIENT_EMAIL
    COL_ORDER_CLIENT     = _C.COL_ORDER_CLIENT
    COL_ORDER_STATUS     = _C.COL_ORDER_STATUS
    COL_ORDER_SOURCE     = _C.COL_ORDER_SOURCE
    COL_ORDER_AMOUNT     = _C.COL_ORDER_AMOUNT
    COL_ORDER_NOTES      = _C.COL_ORDER_NOTES
    COL_ORDER_CREATED_AT = _C.COL_ORDER_CREATED_AT
    COL_EVENT_FROM       = _C.COL_EVENT_FROM
    COL_EVENT_TO         = _C.COL_EVENT_TO
    COL_EVENT_ACTOR      = _C.COL_EVENT_ACTOR
    COL_EVENT_META       = _C.COL_EVENT_META
    COL_EVENT_TIME       = _C.COL_EVENT_TIME

    def __init__(self) -> None:
        self._stores: dict[int, dict[int, dict]] = {}
        self._counter = 0

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    def _store(self, typeId: int) -> dict[int, dict]:
        if typeId not in self._stores:
            self._stores[typeId] = {}
        return self._stores[typeId]

    async def get_object(self, objId: int) -> dict | None:
        for store in self._stores.values():
            if objId in store:
                return store[objId]
        return None

    async def list_objects(
        self,
        typeId: int,
        page: int = 1,
        page_size: int = 50,
        parent_id: int | None = None,
    ) -> list[dict]:
        rows = list(self._store(typeId).values())
        if parent_id is not None:
            rows = [r for r in rows if r.get("_parentId") == parent_id]
        start = (page - 1) * page_size
        return rows[start : start + page_size]

    async def list_children(self, child_typeId: int, parent_id: int) -> list[dict]:
        return [
            obj
            for obj in self._store(child_typeId).values()
            if obj.get("_parentId") == parent_id
        ]

    async def list_orders_by_client(self, client_id: int) -> list[dict]:
        """История заказов клиента — in-memory фильтрация по client_id."""
        return [
            obj
            for obj in self._store(self.T_ORDERS).values()
            if (obj.get("requisites") or {}).get(str(self.COL_ORDER_CLIENT)) == client_id
        ]

    async def create_object(
        self,
        typeId: int,
        value: str = "",
        requisites: dict[str, Any] | None = None,
        parentId: int = 1,
    ) -> dict:
        obj_id = self._next_id()
        obj: dict[str, Any] = {
            "id": obj_id,
            "value": value,
            "typeId": typeId,
            "parentId": parentId,
            "requisites": dict(requisites) if requisites else {},
        }
        if parentId and parentId != 1:
            obj["_parentId"] = parentId
        self._store(typeId)[obj_id] = obj
        return obj

    async def update_object(
        self,
        objId: int,
        value: str | None = None,
        requisites: dict[str, Any] | None = None,
    ) -> dict:
        for store in self._stores.values():
            if objId in store:
                obj = store[objId]
                if value is not None:
                    obj["value"] = value
                if requisites:
                    obj["requisites"] = {**obj.get("requisites", {}), **requisites}
                return obj
        raise KeyError(f"Object {objId} not found")

    async def find_by_field(self, typeId: int, col_id: int, value: str) -> dict | None:
        for obj in self._store(typeId).values():
            req = obj.get("requisites") or {}
            if req.get(str(col_id)) == value:
                return obj
        return None

    async def find_user_by_login(self, login: str) -> dict | None:
        return await self.find_by_field(self.T_USERS, self.COL_USER_LOGIN, login)

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
        if self.T_EVENTS:
            await self.create_object(
                self.T_EVENTS,
                value="",
                requisites={
                    str(self.COL_EVENT_FROM): "",
                    str(self.COL_EVENT_TO): "NEW",
                    str(self.COL_EVENT_ACTOR): actor,
                    str(self.COL_EVENT_META): json.dumps({"source": source}),
                },
                parentId=order["id"],
            )
        return order

    async def import_preview(self, file_bytes: bytes, filename: str) -> dict:
        """Симулируем отказ Integram → тесты проверяют openpyxl fallback."""
        raise IntegramError("FakeIntegramClient: import_preview not supported")

    async def import_xlsx(
        self,
        file_bytes: bytes,
        filename: str,
        typeId: int,
        mapping: dict | None = None,
    ) -> dict:
        """Симулируем отказ Integram → тесты проверяют openpyxl fallback."""
        raise IntegramError("FakeIntegramClient: import_xlsx not supported")

    async def close(self) -> None:
        pass
