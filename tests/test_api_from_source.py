"""test_api_from_source.py — интеграционный тест POST /orders/from-source."""

import pytest


API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY}


class TestOrderFromSource:
    def test_messenger_creates_client_and_order(self, client):
        resp = client.post("/orders/from-source", headers=HEADERS, json={
            "source": "MESSENGER",
            "client": {"phone": "+79001112233", "name": "Тест"},
            "raw": {"messenger": "telegram", "chat_id": 111, "text": "Хочу мёд"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["source"] == "MESSENGER"
        assert data["status"] == "NEW"
        assert data["payload"]["messenger"] == "telegram"

    def test_uds_order(self, client):
        resp = client.post("/orders/from-source", headers=HEADERS, json={
            "source": "UDS",
            "client": {"phone": "+79002223344"},
            "raw": {"id": "uds-999", "total": 1500, "paid": True},
        })
        assert resp.status_code == 201
        assert resp.json()["payload"]["uds_order_id"] == "uds-999"

    def test_dedup_same_client_two_orders(self, client):
        """Два заказа от одного клиента — не дубль."""
        payload = {
            "source": "MESSENGER",
            "client": {"phone": "+79003334455"},
            "raw": {"text": "заказ 1"},
        }
        r1 = client.post("/orders/from-source", headers=HEADERS, json=payload)
        payload["raw"]["text"] = "заказ 2"
        r2 = client.post("/orders/from-source", headers=HEADERS, json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["client_id"] == r2.json()["client_id"]

    def test_no_client_info_returns_422(self, client):
        resp = client.post("/orders/from-source", headers=HEADERS, json={
            "source": "MESSENGER",
            "client": {},
            "raw": {},
        })
        assert resp.status_code == 422

    def test_no_api_key_returns_403(self, client):
        resp = client.post("/orders/from-source", json={
            "source": "MESSENGER",
            "client": {"phone": "+79009999999"},
            "raw": {},
        })
        assert resp.status_code == 403
