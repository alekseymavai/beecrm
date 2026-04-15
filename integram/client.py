"""integram/client.py — async HTTP клиент Integram V2 API."""

import json
import logging
from typing import Any

import httpx

from integram.exceptions import IntegramError, IntegramNotFoundError

logger = logging.getLogger(__name__)


class IntegramClient:
    IAM  = "https://ai2o.online/api/v2/iam"

    T_CLIENTS  = 16
    T_ORDERS   = 17
    T_EVENTS   = 37   # child-таблица "История заказов" (parentTypeId=17)
    T_STATUSES = 14
    T_SOURCES  = 15
    T_PRODUCTS = 52

    # ── Users ─────────────────────────────────────────────────────────────────
    T_USER_ROLES    = 230  # «Роли пользователей» (Integram UI, read-only via V2)
    T_USERS         = 72   # «Пользователи бота» — V2-writable таблица для auth
    ROLE_ADMIN_ID   = 231
    ROLE_MANAGER_ID = 232
    ROLE_NAMES: dict[int, str] = {231: "Администратор", 232: "Менеджер"}

    COL_USER_LOGIN  = 73   # tg_id — используется как CRM-логин
    COL_USER_HASH   = 111  # crm_hash (добавлена в таблицу 72)
    COL_USER_ROLE   = 112  # crm_role (добавлена в таблицу 72, текстовое значение)
    COL_USER_ACTIVE = 76   # is_active

    COL_PRODUCT_PRICE       = 53
    COL_PRODUCT_CATEGORY    = 54
    COL_PRODUCT_STOCK       = 55
    COL_PRODUCT_ACTIVE      = 56
    COL_PRODUCT_DESCRIPTION = 57

    STATUS_MAP = {
        "NEW":         18,
        "CONFIRMED":   190,
        "IN_PROGRESS": 19,
        "DONE":        20,
        "CANCELLED":   21,
    }
    SOURCE_MAP = {
        "UDS":       22,
        "MESSENGER": 23,
        "TABLE":     25,
    }

    # Col IDs — Клиенты (typeId 16)
    COL_CLIENT_NOTES = 27
    COL_CLIENT_PHONE = 28
    COL_CLIENT_EMAIL = 29

    # Col IDs — Заказы (typeId 17)
    COL_ORDER_CLIENT     = 30   # ref → Клиенты
    COL_ORDER_STATUS     = 31   # ref → Статусы
    COL_ORDER_SOURCE     = 32   # ref → Источники
    COL_ORDER_AMOUNT     = 33
    COL_ORDER_NOTES      = 34   # memo — JSON payload
    COL_ORDER_CREATED_AT = 35

    # Col IDs — История заказов (typeId 37)
    COL_EVENT_FROM   = 38
    COL_EVENT_TO     = 39
    COL_EVENT_ACTOR  = 40
    COL_EVENT_META   = 41
    COL_EVENT_TIME   = 42

    def __init__(self, login: str, password: str, token: str | None = None, workspace: str = "beecrm") -> None:
        self._login    = login
        self._password = password
        self._token    = token
        self._http     = httpx.AsyncClient(timeout=30.0)
        self.BASE      = f"https://ai2o.online/api/v2/{workspace}"

    @classmethod
    async def authenticate(cls, login: str, password: str, workspace: str = "beecrm") -> "IntegramClient":
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
            return data
        if isinstance(data, dict):
            return data.get("rows", data.get("items", data.get("data", [])))
        return []

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
            result.extend(rows)
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
        notes = json.dumps({"source": source, "payload": payload}, ensure_ascii=False)
        order = await self.create_object(
            self.T_ORDERS,
            value="",
            requisites={
                str(self.COL_ORDER_CLIENT): client_id,
                str(self.COL_ORDER_STATUS): status_id,
                str(self.COL_ORDER_SOURCE): self.SOURCE_MAP.get(source, 0),
                str(self.COL_ORDER_NOTES):  notes,
            },
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
