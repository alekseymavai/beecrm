"""tests/test_mappers.py — тесты для integram/mappers.py."""

import json

import pytest

from integram.client import (
    IntegramClient,
    _alias_num,
    _alias_ref_id,
    _alias_ref_name,
    _normalize_alias_row,
    _unix_to_iso,
)
from integram.mappers import igm_to_client, igm_to_event, igm_to_order, igm_to_product

# ---------------------------------------------------------------------------
# Вспомогательные константы (реальные значения из IntegramClient)
# ---------------------------------------------------------------------------
C = IntegramClient  # алиас для краткости

PHONE_KEY = str(C.COL_CLIENT_PHONE)   # "28"
EMAIL_KEY = str(C.COL_CLIENT_EMAIL)   # "29"

ORDER_CLIENT_KEY     = str(C.COL_ORDER_CLIENT)      # "30"
ORDER_STATUS_KEY     = str(C.COL_ORDER_STATUS)      # "31"
ORDER_NOTES_KEY      = str(C.COL_ORDER_NOTES) if C.COL_ORDER_NOTES is not None else None
ORDER_CREATED_AT_KEY = str(C.COL_ORDER_CREATED_AT)  # "35"

PRODUCT_PRICE_KEY       = str(C.COL_PRODUCT_PRICE)
PRODUCT_CATEGORY_KEY    = str(C.COL_PRODUCT_CATEGORY)
PRODUCT_STOCK_KEY       = str(C.COL_PRODUCT_STOCK) if C.COL_PRODUCT_STOCK is not None else None
PRODUCT_ACTIVE_KEY      = str(C.COL_PRODUCT_ACTIVE)
PRODUCT_DESCRIPTION_KEY = str(C.COL_PRODUCT_DESCRIPTION)

EVENT_FROM_KEY  = str(C.COL_EVENT_FROM)   # "38"
EVENT_TO_KEY    = str(C.COL_EVENT_TO)     # "39"
EVENT_ACTOR_KEY = str(C.COL_EVENT_ACTOR)  # "40"
EVENT_META_KEY  = str(C.COL_EVENT_META)   # "41"
EVENT_TIME_KEY  = str(C.COL_EVENT_TIME)   # "42"

# STATUS_MAP: "NEW"->18, "CONFIRMED"->190, "IN_PROGRESS"->19, "DONE"->20, "CANCELLED"->21
REVERSE_STATUS = {v: k for k, v in C.STATUS_MAP.items()}


# ===========================================================================
# igm_to_client
# ===========================================================================

class TestIgmToClient:
    def _row(self, **overrides):
        row = {
            "id": 42,
            "value": "Иван Петров",
            "createdAt": "2024-01-10T10:00:00+00:00",
            "updatedAt": "2024-01-11T10:00:00+00:00",
            "requisites": {
                PHONE_KEY: "+79001234567",
                EMAIL_KEY: "ivan@example.com",
            },
        }
        row.update(overrides)
        return row

    def test_normal(self):
        result = igm_to_client(self._row())
        assert result["id"] == 42
        assert result["name"] == "Иван Петров"
        assert result["phone"] == "+79001234567"
        assert result["email"] == "ivan@example.com"
        assert result["created_at"] == "2024-01-10T10:00:00+00:00"
        assert result["updated_at"] == "2024-01-11T10:00:00+00:00"

    def test_missing_phone_and_email(self):
        row = self._row()
        row["requisites"] = {}
        result = igm_to_client(row)
        assert result["phone"] is None
        assert result["email"] is None

    def test_none_requisites(self):
        row = self._row()
        row["requisites"] = None
        result = igm_to_client(row)
        assert result["phone"] is None
        assert result["email"] is None

    def test_missing_name(self):
        row = self._row()
        row.pop("value", None)
        result = igm_to_client(row)
        assert result["name"] is None

    def test_fallback_created_at(self):
        row = self._row()
        row.pop("createdAt", None)
        row["created_at"] = "2024-02-01T00:00:00+00:00"
        result = igm_to_client(row)
        assert result["created_at"] == "2024-02-01T00:00:00+00:00"

    def test_no_dates_uses_now(self):
        result = igm_to_client({"id": 1})
        # Должен вернуть ISO-строку без исключения
        assert result["created_at"]
        assert "T" in result["created_at"]

    def test_empty_dict_no_exception(self):
        """Минимальный вызов — только id обязателен через row['id']."""
        with pytest.raises(KeyError):
            # row без 'id' должен поднять KeyError (ожидаемое поведение)
            igm_to_client({})

    def test_empty_dict_with_id(self):
        result = igm_to_client({"id": 99})
        assert result["id"] == 99
        assert result["phone"] is None
        assert result["email"] is None


# ===========================================================================
# igm_to_order
# ===========================================================================

class TestIgmToOrder:
    def _notes(self, source="MESSENGER", payload=None):
        return json.dumps({"source": source, "payload": payload or {"qty": 2}})

    def _row(self, **overrides):
        status_id = C.STATUS_MAP["IN_PROGRESS"]
        reqs = {
            ORDER_CLIENT_KEY:     "77",
            ORDER_STATUS_KEY:     str(status_id),
            ORDER_CREATED_AT_KEY: "2024-03-01T08:00:00+00:00",
        }
        if ORDER_NOTES_KEY is not None:
            reqs[ORDER_NOTES_KEY] = self._notes()
        row = {
            "id": 100,
            "createdAt": "2024-03-01T08:00:00+00:00",
            "updatedAt": "2024-03-02T08:00:00+00:00",
            "requisites": reqs,
        }
        row.update(overrides)
        return row

    def test_normal(self):
        result = igm_to_order(self._row())
        assert result["id"] == 100
        assert result["client_id"] == 77
        assert result["status"] == "IN_PROGRESS"
        assert result["source"] == "MESSENGER"
        if ORDER_NOTES_KEY is not None:
            assert result["payload"] == {"qty": 2}
        else:
            assert result["payload"] == {}
        assert result["created_at"] == "2024-03-01T08:00:00+00:00"

    def test_status_new_when_empty(self):
        row = self._row()
        row["requisites"].pop(ORDER_STATUS_KEY)
        result = igm_to_order(row)
        assert result["status"] == "NEW"

    def test_status_empty_string(self):
        row = self._row()
        row["requisites"][ORDER_STATUS_KEY] = ""
        result = igm_to_order(row)
        assert result["status"] == "NEW"

    def test_all_status_values(self):
        for status_str, status_id in C.STATUS_MAP.items():
            row = self._row()
            row["requisites"][ORDER_STATUS_KEY] = str(status_id)
            result = igm_to_order(row)
            assert result["status"] == status_str

    @pytest.mark.skipif(ORDER_NOTES_KEY is None, reason="usadba has no notes column")
    def test_invalid_notes_json(self):
        row = self._row()
        row["requisites"][ORDER_NOTES_KEY] = "{not valid json!!!"
        result = igm_to_order(row)
        # notes -> {} fallback
        assert result["source"] == "MESSENGER"
        assert result["payload"] == {}

    @pytest.mark.skipif(ORDER_NOTES_KEY is None, reason="usadba has no notes column")
    def test_none_notes(self):
        row = self._row()
        row["requisites"][ORDER_NOTES_KEY] = None
        result = igm_to_order(row)
        assert result["source"] == "MESSENGER"

    def test_client_from_row_client_dict(self):
        """client_id берётся из row['client']['id'] если нет в requisites."""
        row = self._row()
        row["requisites"].pop(ORDER_CLIENT_KEY)
        row["client"] = {"id": 55}
        result = igm_to_order(row)
        assert result["client_id"] == 55

    def test_client_from_row_client_int(self):
        row = self._row()
        row["requisites"].pop(ORDER_CLIENT_KEY)
        row["client"] = 88
        result = igm_to_order(row)
        assert result["client_id"] == 88

    def test_none_requisites(self):
        row = {"id": 5, "requisites": None}
        result = igm_to_order(row)
        assert result["id"] == 5
        assert result["status"] == "NEW"
        assert result["source"] == "MESSENGER"

    def test_missing_requisites_key(self):
        result = igm_to_order({"id": 7})
        assert result["status"] == "NEW"

    def test_created_at_fallback_chain(self):
        row = self._row()
        row["requisites"].pop(ORDER_CREATED_AT_KEY)
        row.pop("createdAt", None)
        row["created_at"] = "2024-06-01T00:00:00+00:00"
        result = igm_to_order(row)
        assert result["created_at"] == "2024-06-01T00:00:00+00:00"


# ===========================================================================
# igm_to_product
# ===========================================================================

class TestIgmToProduct:
    def _row(self, **overrides):
        reqs = {
            PRODUCT_PRICE_KEY:       "350.50",
            PRODUCT_CATEGORY_KEY:    "Мёд",
            PRODUCT_ACTIVE_KEY:      "1",
            PRODUCT_DESCRIPTION_KEY: "Тёмный мёд с гречки",
        }
        if PRODUCT_STOCK_KEY is not None:
            reqs[PRODUCT_STOCK_KEY] = "10"
        row = {
            "id": 200,
            "value": "Мёд гречишный",
            "createdAt": "2024-04-01T00:00:00+00:00",
            "updatedAt": "2024-04-02T00:00:00+00:00",
            "requisites": reqs,
        }
        row.update(overrides)
        return row

    def test_normal(self):
        result = igm_to_product(self._row())
        assert result["id"] == 200
        assert result["name"] == "Мёд гречишный"
        assert result["price"] == pytest.approx(350.50)
        assert result["category"] == "Мёд"
        if PRODUCT_STOCK_KEY is not None:
            assert result["stock"] == 10
        else:
            assert result["stock"] == 0
        assert result["active"] is True
        assert result["description"] == "Тёмный мёд с гречки"

    def test_none_price_defaults_to_zero(self):
        row = self._row()
        row["requisites"][PRODUCT_PRICE_KEY] = None
        result = igm_to_product(row)
        assert result["price"] == 0.0

    def test_empty_price_defaults_to_zero(self):
        row = self._row()
        row["requisites"][PRODUCT_PRICE_KEY] = ""
        result = igm_to_product(row)
        assert result["price"] == 0.0

    @pytest.mark.skipif(PRODUCT_STOCK_KEY is None, reason="usadba has no stock column")
    def test_none_stock_defaults_to_zero(self):
        row = self._row()
        row["requisites"][PRODUCT_STOCK_KEY] = None
        result = igm_to_product(row)
        assert result["stock"] == 0

    @pytest.mark.skipif(PRODUCT_STOCK_KEY is None, reason="usadba has no stock column")
    def test_float_stock_truncated(self):
        row = self._row()
        row["requisites"][PRODUCT_STOCK_KEY] = "7.9"
        result = igm_to_product(row)
        assert result["stock"] == 7

    def test_active_false(self):
        row = self._row()
        row["requisites"][PRODUCT_ACTIVE_KEY] = None
        result = igm_to_product(row)
        # active_raw is None → True (default)
        assert result["active"] is True

    def test_active_explicit_value(self):
        row = self._row()
        row["requisites"][PRODUCT_ACTIVE_KEY] = 0  # falsy
        result = igm_to_product(row)
        assert result["active"] is False

    def test_none_requisites(self):
        row = {"id": 1, "requisites": None}
        result = igm_to_product(row)
        assert result["price"] == 0.0
        assert result["stock"] == 0
        assert result["active"] is True
        assert result["name"] == ""

    def test_missing_name(self):
        row = self._row()
        row.pop("value", None)
        result = igm_to_product(row)
        assert result["name"] == ""

    def test_empty_dict_with_id(self):
        result = igm_to_product({"id": 99})
        assert result["id"] == 99
        assert result["price"] == 0.0


# ===========================================================================
# igm_to_event
# ===========================================================================

class TestIgmToEvent:
    def _row(self, **overrides):
        row = {
            "id": 300,
            "createdAt": "2024-05-01T12:00:00+00:00",
            "requisites": {
                EVENT_FROM_KEY:  "NEW",
                EVENT_TO_KEY:    "CONFIRMED",
                EVENT_ACTOR_KEY: "operator1",
                EVENT_META_KEY:  json.dumps({"note": "first call"}),
                EVENT_TIME_KEY:  "2024-05-01T12:00:00+00:00",
            },
        }
        row.update(overrides)
        return row

    def test_normal(self):
        result = igm_to_event(self._row(), order_id=100)
        assert result["id"] == 300
        assert result["order_id"] == 100
        assert result["from_status"] == "NEW"
        assert result["to_status"] == "CONFIRMED"
        assert result["actor"] == "operator1"
        assert result["meta"] == {"note": "first call"}
        assert result["created_at"] == "2024-05-01T12:00:00+00:00"

    def test_from_status_none_when_missing(self):
        row = self._row()
        row["requisites"].pop(EVENT_FROM_KEY)
        result = igm_to_event(row, order_id=1)
        assert result["from_status"] is None

    def test_from_status_empty_string_becomes_none(self):
        row = self._row()
        row["requisites"][EVENT_FROM_KEY] = ""
        result = igm_to_event(row, order_id=1)
        assert result["from_status"] is None

    def test_meta_none_when_null_json(self):
        row = self._row()
        row["requisites"][EVENT_META_KEY] = "null"
        result = igm_to_event(row, order_id=1)
        assert result["meta"] is None

    def test_meta_none_when_invalid_json(self):
        row = self._row()
        row["requisites"][EVENT_META_KEY] = "not-json"
        result = igm_to_event(row, order_id=1)
        assert result["meta"] is None

    def test_meta_none_when_missing(self):
        row = self._row()
        row["requisites"].pop(EVENT_META_KEY)
        result = igm_to_event(row, order_id=1)
        assert result["meta"] is None

    def test_actor_none_when_missing(self):
        row = self._row()
        row["requisites"].pop(EVENT_ACTOR_KEY)
        result = igm_to_event(row, order_id=1)
        assert result["actor"] is None

    def test_created_at_fallback_to_row_createdAt(self):
        row = self._row()
        row["requisites"].pop(EVENT_TIME_KEY)
        result = igm_to_event(row, order_id=1)
        assert result["created_at"] == "2024-05-01T12:00:00+00:00"

    def test_created_at_fallback_to_created_at(self):
        row = self._row()
        row["requisites"].pop(EVENT_TIME_KEY)
        row.pop("createdAt", None)
        row["created_at"] = "2024-07-01T00:00:00+00:00"
        result = igm_to_event(row, order_id=1)
        assert result["created_at"] == "2024-07-01T00:00:00+00:00"

    def test_none_requisites(self):
        row = {"id": 1, "requisites": None}
        result = igm_to_event(row, order_id=5)
        assert result["from_status"] is None
        assert result["to_status"] == "NEW"
        assert result["actor"] is None
        assert result["meta"] is None

    def test_to_status_default_new(self):
        row = self._row()
        row["requisites"].pop(EVENT_TO_KEY)
        result = igm_to_event(row, order_id=1)
        assert result["to_status"] == "NEW"

    def test_order_id_propagated(self):
        result = igm_to_event(self._row(), order_id=9999)
        assert result["order_id"] == 9999


# ===========================================================================
# Helpers: _alias_ref_id, _alias_num, _alias_ref_name, _unix_to_iso
# ===========================================================================

class TestAliasHelpers:
    def test_ref_id_normal(self):
        assert _alias_ref_id("Отправлен (id:133)") == "133"

    def test_ref_id_anchored(self):
        # Name contains (id:999) but not at end — must NOT match the inner one
        assert _alias_ref_id("Мёд (id:999) липовый (id:140)") == "140"

    def test_ref_id_no_suffix(self):
        assert _alias_ref_id("Просто текст") is None

    def test_ref_id_empty(self):
        assert _alias_ref_id("") is None
        assert _alias_ref_id(None) is None

    def test_ref_name_normal(self):
        assert _alias_ref_name("Мёд и пчелопродукты (id:140)") == "Мёд и пчелопродукты"

    def test_ref_name_no_suffix(self):
        assert _alias_ref_name("Просто текст") == "Просто текст"

    def test_num_with_ref(self):
        assert _alias_num("78 (id:1300)") == "78"
        assert _alias_num("0 (id:6950)") == "0"

    def test_num_plain_float(self):
        assert _alias_num("350.50") == "350.50"

    def test_num_none(self):
        assert _alias_num(None) is None

    def test_unix_to_iso(self):
        result = _unix_to_iso("0")
        assert "1970" in result
        assert "T" in result

    def test_unix_to_iso_none(self):
        assert _unix_to_iso(None) is None
        assert _unix_to_iso("") is None

    def test_unix_to_iso_invalid(self):
        # Invalid input → returns raw string (no exception)
        result = _unix_to_iso("not-a-number")
        assert result == "not-a-number"


# ===========================================================================
# _normalize_alias_row
# ===========================================================================

class TestNormalizeAliasRow:
    """Unit-тесты нормализации alias-format → requisites-format."""

    C = IntegramClient

    def _order_alias_row(self, **overrides):
        row = {
            "id": 11452,
            "name": "Заказ 527609",
            "Номер": "527609",
            "Статус заказа": f"Отправлен (id:{self.C.STATUS_MAP['DONE']})",
            "Источник": f"ВК (id:{self.C.SOURCE_MAP['TABLE']})",
            "Клиент": "Иванов (id:42)",
            "Дата": "1760140800",
            "Сумма": "1500 (id:9999)",
        }
        row.update(overrides)
        return row

    def test_passthrough_if_requisites_present(self):
        row = {"id": 1, "requisites": {"87": "133"}}
        result = _normalize_alias_row(self.C.T_ORDERS, row)
        assert result is row  # same object, no copy

    def test_order_status_extracted(self):
        row = self._order_alias_row()
        result = _normalize_alias_row(self.C.T_ORDERS, row)
        assert result["requisites"][str(self.C.COL_ORDER_STATUS)] == str(self.C.STATUS_MAP["DONE"])

    def test_order_source_extracted(self):
        row = self._order_alias_row()
        result = _normalize_alias_row(self.C.T_ORDERS, row)
        assert result["requisites"][str(self.C.COL_ORDER_SOURCE)] == str(self.C.SOURCE_MAP["TABLE"])

    def test_order_client_extracted(self):
        row = self._order_alias_row()
        result = _normalize_alias_row(self.C.T_ORDERS, row)
        assert result["requisites"][str(self.C.COL_ORDER_CLIENT)] == "42"

    def test_order_date_converted_to_iso(self):
        row = self._order_alias_row()
        result = _normalize_alias_row(self.C.T_ORDERS, row)
        date_val = result["requisites"][str(self.C.COL_ORDER_CREATED_AT)]
        assert "T" in date_val  # ISO format

    def test_order_amount_numeric(self):
        row = self._order_alias_row()
        result = _normalize_alias_row(self.C.T_ORDERS, row)
        assert result["requisites"][str(self.C.COL_ORDER_AMOUNT)] == "1500"

    def test_order_missing_client_alias(self):
        row = self._order_alias_row()
        row.pop("Клиент")
        result = _normalize_alias_row(self.C.T_ORDERS, row)
        assert str(self.C.COL_ORDER_CLIENT) not in result["requisites"]

    def test_order_value_set_from_name(self):
        row = self._order_alias_row()
        result = _normalize_alias_row(self.C.T_ORDERS, row)
        assert result["value"] == "Заказ 527609"

    def test_client_phone_email(self):
        row = {
            "id": 556,
            "name": "Артем Бывальцев",
            "Телефон": "+79001234567",
            "Email": "artem@example.com",
            "Дата регистрации": "1762905600",
        }
        result = _normalize_alias_row(self.C.T_CLIENTS, row)
        assert result["requisites"][str(self.C.COL_CLIENT_PHONE)] == "+79001234567"
        assert result["requisites"][str(self.C.COL_CLIENT_EMAIL)] == "artem@example.com"

    def test_client_created_at_injected(self):
        row = {"id": 556, "name": "Тест", "Дата регистрации": "0"}
        result = _normalize_alias_row(self.C.T_CLIENTS, row)
        assert result.get("createdAt") and "1970" in result["createdAt"]

    def test_product_price_and_category(self):
        row = {
            "id": 155,
            "name": "Мёд липовый",
            "Цена": "1500 (id:999)",
            "Категория": "Мёд и пчелопродукты (id:140)",
            "В наличии": "1",
        }
        result = _normalize_alias_row(self.C.T_PRODUCTS, row)
        assert result["requisites"][str(self.C.COL_PRODUCT_PRICE)] == "1500"
        assert result["requisites"][str(self.C.COL_PRODUCT_CATEGORY)] == "Мёд и пчелопродукты"
        assert result["requisites"][str(self.C.COL_PRODUCT_ACTIVE)] == "1"

    def test_unknown_typeId_returns_empty_requisites(self):
        row = {"id": 1, "SomeAlias": "value"}
        result = _normalize_alias_row(9999, row)
        assert result["requisites"] == {}


# ===========================================================================
# Alias-format end-to-end: normalize → mapper
# ===========================================================================

class TestAliasFormatEndToEnd:
    """Тесты полного пути: alias-row → _normalize_alias_row → igm_to_* mapper."""

    C = IntegramClient

    def test_igm_to_order_alias_status_and_client(self):
        status_id = self.C.STATUS_MAP["DONE"]
        row = {
            "id": 11452,
            "name": "Заказ 527609",
            "Статус заказа": f"Отправлен (id:{status_id})",
            "Клиент": "Иванов Иван (id:42)",
            "Дата": "1760140800",
        }
        normalized = _normalize_alias_row(self.C.T_ORDERS, row)
        result = igm_to_order(normalized)
        assert result["status"] == "DONE"
        assert result["client_id"] == 42
        assert "T" in result["created_at"]

    def test_igm_to_order_alias_source_from_ref(self):
        source_id = self.C.SOURCE_MAP["TABLE"]
        row = {
            "id": 1,
            "name": "Заказ 1",
            "Источник": f"ВК (id:{source_id})",
        }
        normalized = _normalize_alias_row(self.C.T_ORDERS, row)
        result = igm_to_order(normalized)
        assert result["source"] == "TABLE"

    def test_igm_to_order_alias_source_default_messenger(self):
        row = {"id": 2, "name": "Заказ 2"}
        normalized = _normalize_alias_row(self.C.T_ORDERS, row)
        result = igm_to_order(normalized)
        assert result["source"] == "MESSENGER"

    def test_igm_to_client_alias_phone_email(self):
        row = {
            "id": 556,
            "name": "Артем Бывальцев",
            "Телефон": "+79992192781",
            "Email": "artem@test.com",
        }
        normalized = _normalize_alias_row(self.C.T_CLIENTS, row)
        result = igm_to_client(normalized)
        assert result["phone"] == "+79992192781"
        assert result["email"] == "artem@test.com"
        assert result["name"] == "Артем Бывальцев"

    def test_igm_to_product_alias_price_category_active(self):
        row = {
            "id": 155,
            "name": "Мёд липовый",
            "Цена": "78 (id:1300)",
            "Категория": "Мёд и пчелопродукты (id:140)",
            "В наличии": "1",
            "Описание": "Свежий мёд",
        }
        normalized = _normalize_alias_row(self.C.T_PRODUCTS, row)
        result = igm_to_product(normalized)
        assert result["price"] == pytest.approx(78.0)
        assert result["category"] == "Мёд и пчелопродукты"
        assert result["active"] is True
        assert result["description"] == "Свежий мёд"

    def test_igm_to_product_alias_zero_price(self):
        row = {"id": 1, "name": "Тест", "Цена": "0 (id:1500)", "В наличии": "1"}
        normalized = _normalize_alias_row(self.C.T_PRODUCTS, row)
        result = igm_to_product(normalized)
        assert result["price"] == 0.0
