"""FakeIntegramClient — in-memory имитация Integram для тестов."""

import json
from typing import Any

from integram.exceptions import IntegramError


class FakeIntegramClient:
    """In-memory реализация IntegramClient. Не делает HTTP-запросов."""

    T_CLIENTS = 16
    T_ORDERS = 17
    T_EVENTS = 999   # ненулевое значение — события включены в тестах
    T_STATUSES = 14
    T_SOURCES = 15
    T_PRODUCTS = 52

    T_USER_ROLES    = 200   # фиктивный ID для тестов
    T_USERS         = 201
    ROLE_ADMIN_ID   = 500
    ROLE_MANAGER_ID = 501
    ROLE_NAMES: dict[int, str] = {500: "Администратор", 501: "Менеджер"}

    COL_USER_LOGIN  = 202
    COL_USER_HASH   = 203
    COL_USER_ROLE   = 204
    COL_USER_ACTIVE = 205

    COL_PRODUCT_PRICE = 53
    COL_PRODUCT_CATEGORY = 54
    COL_PRODUCT_STOCK = 55
    COL_PRODUCT_ACTIVE = 56
    COL_PRODUCT_DESCRIPTION = 57

    STATUS_MAP = {
        "NEW": 18,
        "CONFIRMED": 190,
        "IN_PROGRESS": 19,
        "DONE": 20,
        "CANCELLED": 21,
    }
    SOURCE_MAP = {
        "UDS": 22,
        "MESSENGER": 23,
        "TABLE": 25,
    }

    COL_CLIENT_NOTES = 27
    COL_CLIENT_PHONE = 28
    COL_CLIENT_EMAIL = 29
    COL_ORDER_CLIENT = 30
    COL_ORDER_STATUS = 31
    COL_ORDER_SOURCE = 32
    COL_ORDER_AMOUNT = 33
    COL_ORDER_NOTES = 34
    COL_ORDER_CREATED_AT = 35
    COL_EVENT_FROM = 38
    COL_EVENT_TO = 39
    COL_EVENT_ACTOR = 40
    COL_EVENT_META = 41
    COL_EVENT_TIME = 42

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

    async def create_order_with_event(
        self,
        client_id: int,
        status_id: int,
        source: str,
        payload: dict,
        actor: str = "system",
    ) -> dict:
        notes = json.dumps({"source": source, "payload": payload}, ensure_ascii=False)
        order = await self.create_object(
            self.T_ORDERS,
            value="",
            requisites={
                str(self.COL_ORDER_CLIENT): client_id,
                str(self.COL_ORDER_STATUS): status_id,
                str(self.COL_ORDER_SOURCE): self.SOURCE_MAP.get(source, 0),
                str(self.COL_ORDER_NOTES): notes,
            },
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
