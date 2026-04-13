"""test_uds_poller.py — тесты UDSPoller (in-memory, без HTTP)."""

import pytest
import pytest_asyncio
from tests.mocks.integram_mock import FakeIntegramClient
from uds.client import UDSAuthError
from uds.poller import UDSPoller

# ── Фикстура: минимальный UDS order detail ────────────────────────────────────

_ORDER_DETAIL = {
    "id": 42,
    "state": "ACCEPTED",
    "paymentStatus": "PAID",
    "dateCreated": "2026-04-01T12:00:00Z",
    "customer": {"displayName": "Тест Тестов", "phone": "+79991234567"},
    "deliveryData": {
        "receiverName": "Тест Тестов",
        "receiverPhone": "+79991234567",
        "address": "г. Тест",
        "userComment": "",
        "deliveryCase": {"name": "Самовывоз", "value": "0"},
    },
    "purchase": {"total": 500.0, "extras": {"delivery": 0}},
    "goods": {
        "rows": [
            {"id": 1, "name": "Мёд", "qty": 1, "price": 500.0, "type": "PRODUCT"},
        ]
    },
}

_ORDER_DETAIL_2 = {**_ORDER_DETAIL, "id": 43, "customer": {"displayName": "Другой", "phone": "+79990000001"}}
_ORDER_DELETED = {**_ORDER_DETAIL, "id": 44, "state": "DELETED"}


class FakeUDSClient:
    """In-memory UDS клиент — не делает HTTP."""

    def __init__(self, orders=None, detail_map=None, raise_auth_on=None, raise_error_on=None):
        # orders — список строк rows для get_orders_page
        self._orders = orders or [{"id": 42}]
        # detail_map — {order_id: detail_dict}
        self._detail_map = detail_map or {42: _ORDER_DETAIL}
        # raise_auth_on — set of order_ids where get_order_detail raises UDSAuthError
        self._raise_auth_on = raise_auth_on or set()
        # raise_error_on — set of order_ids where get_order_detail raises RuntimeError
        self._raise_error_on = raise_error_on or set()

    async def get_orders_page(self, offset: int, limit: int = 50) -> dict:
        return {"total": len(self._orders), "rows": self._orders}

    async def get_order_detail(self, order_id: int) -> dict:
        if order_id in self._raise_auth_on:
            raise UDSAuthError("token expired")
        if order_id in self._raise_error_on:
            raise RuntimeError(f"network error for {order_id}")
        return self._detail_map[order_id]

    async def close(self) -> None:
        pass


# ── Тесты ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tick_creates_order():
    igm = FakeIntegramClient()
    uds_client = FakeUDSClient()
    poller = UDSPoller(igm, _uds_client=uds_client)

    await poller._tick()

    clients = list(igm._store(igm.T_CLIENTS).values())
    orders = list(igm._store(igm.T_ORDERS).values())
    assert len(clients) == 1
    assert len(orders) == 1
    assert "42" in poller.seen_ids


@pytest.mark.asyncio
async def test_tick_deduplicates():
    igm = FakeIntegramClient()
    uds_client = FakeUDSClient()
    poller = UDSPoller(igm, _uds_client=uds_client)

    await poller._tick()
    await poller._tick()

    orders = list(igm._store(igm.T_ORDERS).values())
    assert len(orders) == 1  # второй tick не создал дубль


@pytest.mark.asyncio
async def test_tick_skips_deleted():
    igm = FakeIntegramClient()
    uds_client = FakeUDSClient(
        orders=[{"id": 44}],
        detail_map={44: _ORDER_DELETED},
    )
    poller = UDSPoller(igm, _uds_client=uds_client)

    await poller._tick()

    orders = list(igm._store(igm.T_ORDERS).values())
    assert len(orders) == 0  # DELETED пропущен


@pytest.mark.asyncio
async def test_auth_error_stops_poller():
    igm = FakeIntegramClient()
    uds_client = FakeUDSClient(
        orders=[{"id": 42}],
        detail_map={42: _ORDER_DETAIL},
        raise_auth_on={42},
    )
    poller = UDSPoller(igm, _uds_client=uds_client)
    await poller.start()

    await poller._tick()

    st = poller.status()
    assert st["error"] is True  # bool — error присутствует

    await poller.stop()


@pytest.mark.asyncio
async def test_single_order_error_continues():
    igm = FakeIntegramClient()
    uds_client = FakeUDSClient(
        orders=[{"id": 42}, {"id": 43}],
        detail_map={42: _ORDER_DETAIL, 43: _ORDER_DETAIL_2},
        raise_error_on={42},  # первый падает, второй должен пройти
    )
    poller = UDSPoller(igm, _uds_client=uds_client)

    await poller._tick()

    orders = list(igm._store(igm.T_ORDERS).values())
    assert len(orders) == 1  # только второй заказ создан
    assert "43" in poller.seen_ids
    assert "42" not in poller.seen_ids
