"""test_uds_mapper.py — тесты маппинга UDS order detail → BEECRM."""

import pytest
from schemas.enums import OrderStatus
from uds.mapper import UDS_STATUS_MAP, parse_order

FULL_DETAIL = {
    "id": 12345,
    "dateCreated": "2026-04-01T10:00:00Z",
    "state": "ACCEPTED",
    "paymentStatus": "PAID",
    "customer": {
        "displayName": "Иван Петров",
        "phone": "+79161234567",
    },
    "deliveryData": {
        "receiverName": "Иван Петров",
        "receiverPhone": "+79161234567",
        "address": "Москва, ул. Ленина 1",
        "userComment": "Позвоните перед доставкой",
        "deliveryCase": {"name": "СДЭК", "value": "350"},
    },
    "purchase": {
        "total": 2850.0,
        "extras": {"delivery": 350},
    },
    "goods": {
        "rows": [
            {"id": 999, "name": "Мёд липовый 0.5кг", "qty": 2, "price": 1250.0, "type": "PRODUCT"},
            {"id": 998, "name": "Коробка", "qty": 1, "price": 0, "type": "OPTION"},
        ]
    },
}

MINIMAL_DETAIL: dict = {}


class TestParseOrderFull:
    def test_parse_order_full(self):
        result = parse_order(FULL_DETAIL)
        assert result["uds_order_id"] == 12345
        assert result["state"] == "ACCEPTED"
        assert result["payment_status"] == "PAID"
        assert result["date_created"] == "2026-04-01T10:00:00Z"
        assert result["total"] == 2850.0
        assert result["delivery_cost"] == 350.0
        assert result["items_total"] == 2500.0
        assert result["delivery_name"] == "СДЭК"
        assert result["customer_name"] == "Иван Петров"
        assert result["customer_phone"] == "+79161234567"
        assert result["address"] == "Москва, ул. Ленина 1"
        assert result["comment"] == "Позвоните перед доставкой"


class TestParseOrderMinimal:
    def test_parse_order_minimal(self):
        result = parse_order(MINIMAL_DETAIL)
        assert result["uds_order_id"] == 0
        assert result["state"] == ""
        assert result["payment_status"] == ""
        assert result["date_created"] == ""
        assert result["total"] == 0.0
        assert result["delivery_cost"] == 0.0
        assert result["items_total"] == 0.0
        assert result["delivery_name"] == ""
        assert result["customer_name"] == ""
        assert result["customer_phone"] == ""
        assert result["address"] == ""
        assert result["comment"] == ""
        assert result["items"] == []


class TestStatusMap:
    def test_status_map_new(self):
        assert UDS_STATUS_MAP["NEW"] == OrderStatus.NEW

    def test_status_map_accepted(self):
        assert UDS_STATUS_MAP["ACCEPTED"] == OrderStatus.CONFIRMED

    def test_status_map_completed(self):
        assert UDS_STATUS_MAP["COMPLETED"] == OrderStatus.COMPLETED

    def test_status_map_cancelled(self):
        assert UDS_STATUS_MAP["CANCELLED"] == OrderStatus.CANCELLED


class TestParseOrderItems:
    def test_parse_order_skips_options(self):
        result = parse_order(FULL_DETAIL)
        names = [item["name"] for item in result["items"]]
        assert "Мёд липовый 0.5кг" in names
        assert "Коробка" not in names

    def test_parse_order_items_fields(self):
        result = parse_order(FULL_DETAIL)
        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["name"] == "Мёд липовый 0.5кг"
        assert item["qty"] == 2
        assert item["price"] == 1250.0
        assert item["uds_product_id"] == 999
