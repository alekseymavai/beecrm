"""FakeIntegramClient — in-memory имитация Integram для тестов."""

import json
from typing import Any


class FakeIntegramClient:
    """In-memory реализация IntegramClient. Не делает HTTP-запросов."""

    T_CLIENTS = 16
    T_ORDERS = 17
    T_EVENTS = 999   # ненулевое значение — события включены в тестах
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

    COL_CLIENT_NOTES = 27
    COL_CLIENT_PHONE = 28
    COL_CLIENT_EMAIL = 29
    COL_ORDER_CLIENT = 30
    COL_ORDER_STATUS = 31
    COL_ORDER_AMOUNT = 33
    COL_ORDER_NOTES = 34
    COL_ORDER_CREATED_AT = 35

    # col_id → field name для find_by_field
    _COL_TO_FIELD: dict[int, str] = {
        27: "notes",
        28: "phone",
        29: "email",
        30: "client",
        31: "status",
        33: "amount",
        34: "notes",
        35: "created_at",
    }

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

    async def get_object(self, typeId: int, objId: int) -> dict | None:
        return self._store(typeId).get(objId)

    async def list_objects(self, typeId: int, skip: int = 0, limit: int = 20) -> list[dict]:
        rows = list(self._store(typeId).values())
        return rows[skip : skip + limit]

    async def list_children(
        self, parent_typeId: int, parent_id: int, child_typeId: int
    ) -> list[dict]:
        return [
            obj
            for obj in self._store(child_typeId).values()
            if obj.get("_parentId") == parent_id
        ]

    async def create_object(
        self, typeId: int, fields: dict, parentId: int | None = None
    ) -> dict:
        obj_id = self._next_id()
        obj: dict[str, Any] = {"id": obj_id, **fields}
        if parentId is not None:
            obj["_parentId"] = parentId
        self._store(typeId)[obj_id] = obj
        return obj

    async def update_object(self, typeId: int, objId: int, fields: dict) -> dict:
        store = self._store(typeId)
        if objId not in store:
            raise KeyError(f"Object {typeId}/{objId} not found")
        store[objId].update(fields)
        return store[objId]

    async def find_by_field(self, typeId: int, col_id: int, value: str) -> dict | None:
        field = self._COL_TO_FIELD.get(col_id)
        if not field:
            return None
        for obj in self._store(typeId).values():
            if obj.get(field) == value:
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
            {"client": client_id, "status": status_id, "notes": notes},
        )
        if self.T_EVENTS:
            await self.create_object(
                self.T_EVENTS,
                {
                    "from_status": "",
                    "to_status": "NEW",
                    "actor": actor,
                    "meta": json.dumps({"source": source}),
                },
                parentId=order["id"],
            )
        return order

    async def close(self) -> None:
        pass
