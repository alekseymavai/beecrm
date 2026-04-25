"""tests/test_mappers.py — тесты для integram/mappers.py."""

import json

import pytest

from integram.client import IntegramClient
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
