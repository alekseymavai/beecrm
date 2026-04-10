"""tests/test_notify_service.py — тесты NotifyService (без HTTP, mock Bot)."""

from __future__ import annotations

import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# apiary/config.py читает env при импорте через os.environ[] — установим заглушки
os.environ.setdefault("BEEBOTLITE_TOKEN", "test:token")
os.environ.setdefault("BEEBOTLITE_ADMIN_TG_ID", "0")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")

from services.notify_service import NotifyService, _format_message
from tests.mocks.integram_mock import FakeIntegramClient


# ── Вспомогательные объекты ───────────────────────────────────────────────────

def _make_bot() -> MagicMock:
    """Создать mock aiogram Bot с async send_message."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    return bot


def _make_parsed(
    name: str = "Иван Иванов",
    phone: str = "+79991234567",
    total: float | None = 1500.0,
    uds_order_id: int = 42,
) -> dict:
    return {
        "customer_name": name,
        "customer_phone": phone,
        "total": total,
        "uds_order_id": uds_order_id,
        "state": "ACCEPTED",
    }


# ── Тест: формат сообщения ────────────────────────────────────────────────────

def test_format_message_with_total():
    parsed = _make_parsed(name="Иван Иванов", phone="+79991234567", total=1500.0)
    text = _format_message(parsed)
    assert "Иван Иванов" in text
    assert "+79991234567" in text
    assert "1500" in text
    assert "UDS" in text


def test_format_message_without_total():
    parsed = _make_parsed(total=None)
    text = _format_message(parsed)
    assert "Сумма" not in text
    assert "Иван Иванов" in text
    assert "+79991234567" in text


# ── Тест: отправка admin-only (APIARY_T_USERS=0) ──────────────────────────────

@pytest.mark.asyncio
async def test_notify_uses_admin_when_table_not_configured():
    """Если APIARY_T_USERS=0 — уведомление только admin_tg_id."""
    bot = _make_bot()
    igm = FakeIntegramClient()
    admin_id = 111222333

    with patch("apiary.config.APIARY_T_USERS", 0), \
         patch("apiary.config.COL_USER_TG_ID", 0):
        svc = NotifyService(bot=bot, igm=igm, admin_tg_id=admin_id)
        await svc.notify_new_order(_make_parsed())

    bot.send_message.assert_awaited_once()
    call_kwargs = bot.send_message.call_args
    assert call_kwargs.kwargs["chat_id"] == admin_id


# ── Тест: ошибка отправки не прерывает обработку ─────────────────────────────

@pytest.mark.asyncio
async def test_send_error_does_not_propagate():
    """При ошибке send_message исключение поглощается, заказ не падает."""
    bot = _make_bot()
    bot.send_message.side_effect = RuntimeError("Telegram unreachable")
    igm = FakeIntegramClient()

    with patch("apiary.config.APIARY_T_USERS", 0), \
         patch("apiary.config.COL_USER_TG_ID", 0):
        svc = NotifyService(bot=bot, igm=igm, admin_tg_id=999888777)
        # Не должен вызвать исключение
        await svc.notify_new_order(_make_parsed())

    # send_message был вызван (попытка была)
    bot.send_message.assert_awaited_once()


# ── Тест: активные пользователи из Integram ───────────────────────────────────

@pytest.mark.asyncio
async def test_notify_sends_to_active_users_from_integram():
    """Уведомление отправляется всем активным пользователям из APIARY_T_USERS."""
    bot = _make_bot()
    igm = FakeIntegramClient()

    T_USERS = 201
    COL_TG_ID = 301
    COL_ACTIVE = 302
    admin_id = 999

    # Создаём 2 активных и 1 неактивного пользователя в fake Integram
    await igm.create_object(T_USERS, value="user1", requisites={
        str(COL_TG_ID): "111",
        str(COL_ACTIVE): True,
    })
    await igm.create_object(T_USERS, value="user2", requisites={
        str(COL_TG_ID): "222",
        str(COL_ACTIVE): True,
    })
    await igm.create_object(T_USERS, value="user3_inactive", requisites={
        str(COL_TG_ID): "333",
        str(COL_ACTIVE): False,
    })

    with patch("apiary.config.APIARY_T_USERS", T_USERS), \
         patch("apiary.config.COL_USER_TG_ID", COL_TG_ID), \
         patch("apiary.config.COL_USER_ACTIVE", COL_ACTIVE):
        svc = NotifyService(bot=bot, igm=igm, admin_tg_id=admin_id)
        await svc.notify_new_order(_make_parsed())

    assert bot.send_message.await_count == 2
    sent_ids = {c.kwargs["chat_id"] for c in bot.send_message.call_args_list}
    assert 111 in sent_ids
    assert 222 in sent_ids
    assert 333 not in sent_ids
    assert admin_id not in sent_ids


# ── Тест: нет активных пользователей → fallback на admin ─────────────────────

@pytest.mark.asyncio
async def test_notify_fallback_to_admin_when_no_active_users():
    """Если активных пользователей нет — уведомление только admin."""
    bot = _make_bot()
    igm = FakeIntegramClient()

    T_USERS = 201
    COL_TG_ID = 301
    COL_ACTIVE = 302
    admin_id = 777666

    # Только неактивный пользователь
    await igm.create_object(T_USERS, value="user_inactive", requisites={
        str(COL_TG_ID): "555",
        str(COL_ACTIVE): False,
    })

    with patch("apiary.config.APIARY_T_USERS", T_USERS), \
         patch("apiary.config.COL_USER_TG_ID", COL_TG_ID), \
         patch("apiary.config.COL_USER_ACTIVE", COL_ACTIVE):
        svc = NotifyService(bot=bot, igm=igm, admin_tg_id=admin_id)
        await svc.notify_new_order(_make_parsed())

    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.kwargs["chat_id"] == admin_id


# ── Тест: интеграция с UDSPoller ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_poller_calls_notify_after_create_order():
    """UDSPoller вызывает notify_new_order после создания заказа."""
    from uds.poller import UDSPoller
    from uds.client import UDSAuthError

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
        "goods": {"rows": [{"id": 1, "name": "Мёд", "qty": 1, "price": 500.0, "type": "PRODUCT"}]},
    }

    class FakeUDSClient:
        async def get_orders_page(self, offset, limit=50):
            return {"total": 1, "rows": [{"id": 42}]}
        async def get_order_detail(self, order_id):
            return _ORDER_DETAIL
        async def close(self):
            pass

    notify_mock = MagicMock()
    notify_mock.notify_new_order = AsyncMock()

    igm = FakeIntegramClient()
    poller = UDSPoller(igm, _uds_client=FakeUDSClient(), notify_service=notify_mock)
    await poller._tick()

    notify_mock.notify_new_order.assert_awaited_once()
    # Проверяем что передан parsed dict с полями клиента
    call_arg = notify_mock.notify_new_order.call_args.args[0]
    assert "customer_name" in call_arg
    assert "uds_order_id" in call_arg


@pytest.mark.asyncio
async def test_poller_creates_order_even_if_notify_fails():
    """UDSPoller создаёт заказ даже если notify_new_order падает."""
    from uds.poller import UDSPoller

    _ORDER_DETAIL = {
        "id": 55,
        "state": "ACCEPTED",
        "paymentStatus": "PAID",
        "dateCreated": "2026-04-01T12:00:00Z",
        "customer": {"displayName": "Сбой Нотифи", "phone": "+79990000055"},
        "deliveryData": {
            "receiverName": "Сбой Нотифи",
            "receiverPhone": "+79990000055",
            "address": "г. Тест",
            "userComment": "",
            "deliveryCase": {"name": "Самовывоз", "value": "0"},
        },
        "purchase": {"total": 200.0, "extras": {"delivery": 0}},
        "goods": {"rows": []},
    }

    class FakeUDSClient:
        async def get_orders_page(self, offset, limit=50):
            return {"total": 1, "rows": [{"id": 55}]}
        async def get_order_detail(self, order_id):
            return _ORDER_DETAIL
        async def close(self):
            pass

    notify_mock = MagicMock()
    notify_mock.notify_new_order = AsyncMock(side_effect=RuntimeError("Telegram down"))

    igm = FakeIntegramClient()
    poller = UDSPoller(igm, _uds_client=FakeUDSClient(), notify_service=notify_mock)
    await poller._tick()

    # Заказ всё равно создан
    orders = list(igm._store(igm.T_ORDERS).values())
    assert len(orders) == 1
    assert "55" in poller.seen_ids
