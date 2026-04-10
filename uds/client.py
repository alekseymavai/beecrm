"""uds/client.py — HTTP-клиент UDS Admin API."""

import httpx


class UDSError(Exception):
    """Базовый класс ошибок UDS."""


class UDSAuthError(UDSError):
    """401/403 — токен истёк или недействителен."""


class UDSAPIError(UDSError):
    """Прочие HTTP-ошибки UDS API."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"UDS API error {status}: {body}")
        self.status = status
        self.body = body


class UDSAdminClient:
    BASE = "https://api.uds.app/admin"

    def __init__(self, token: str, company_id: str) -> None:
        self._token = token
        self._company_id = company_id
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def get_orders_page(self, offset: int, limit: int = 50) -> dict:
        """GET /companies/{company_id}/goods-orders?max={limit}&offset={offset}"""
        url = f"{self.BASE}/companies/{self._company_id}/goods-orders"
        resp = await self._client.get(url, params={"max": limit, "offset": offset})
        if resp.status_code in (401, 403):
            raise UDSAuthError("UDS Admin token истёк или недействителен")
        if resp.status_code != 200:
            raise UDSAPIError(resp.status_code, resp.text)
        return resp.json()

    async def get_order_detail(self, order_id: int) -> dict:
        """GET /companies/{company_id}/goods-orders/{order_id}"""
        url = f"{self.BASE}/companies/{self._company_id}/goods-orders/{order_id}"
        resp = await self._client.get(url)
        if resp.status_code in (401, 403):
            raise UDSAuthError("UDS Admin token истёк или недействителен")
        if resp.status_code != 200:
            raise UDSAPIError(resp.status_code, resp.text)
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
