"""test_adapters.py — тесты BaseAdapter + адаптеров источников."""

import pytest
from adapters.base import AdapterError
from adapters.uds_adapter import UDSAdapter
from adapters.messenger_adapter import MessengerAdapter
from adapters.table_adapter import TableAdapter


class TestUDSAdapter:
    def test_normalize_valid(self):
        raw = {"id": "123", "items": [{"name": "Мёд", "qty": 2}], "total": 500, "paid": True}
        result = UDSAdapter().normalize(raw)
        assert result["uds_order_id"] == "123"
        assert result["total"] == 500
        assert result["paid"] is True

    def test_normalize_empty(self):
        result = UDSAdapter().normalize({})
        assert result["uds_order_id"] is None
        assert result["items"] == []


class TestMessengerAdapter:
    def test_normalize_telegram(self):
        raw = {"messenger": "telegram", "chat_id": 999, "text": "Хочу мёд"}
        result = MessengerAdapter().normalize(raw)
        assert result["messenger"] == "telegram"
        assert result["message"] == "Хочу мёд"

    def test_normalize_whatsapp(self):
        raw = {"messenger": "whatsapp", "chat_id": "79001234567", "message": "Заказ"}
        result = MessengerAdapter().normalize(raw)
        assert result["chat_id"] == "79001234567"


class TestTableAdapter:
    def test_from_xlsx_row(self):
        row = {"items": ["Мёд 0.5кг"], "manager": "Иван", "source_channel": "ВК"}
        result = TableAdapter.from_xlsx_row(row)
        assert result["manager"] == "Иван"
        assert result["source_channel"] == "ВК"


class TestBaseAdapterSecurity:
    def test_forbidden_keys(self):
        adapter = UDSAdapter()
        with pytest.raises(AdapterError, match="Запрещённые ключи"):
            adapter._validate({"__proto__": "bad"})

    def test_payload_too_large(self):
        adapter = UDSAdapter()
        # список не обрезается — создаём payload > 65536 байт
        big = {"items": ["мёд"] * 10000}
        with pytest.raises(AdapterError, match="превышает лимит"):
            adapter._validate(big)

    def test_long_string_trimmed(self):
        adapter = UDSAdapter()
        result = adapter._validate({"comment": "a" * 3000})
        assert len(result["comment"]) == 2048
