"""test_products.py — тесты Products API (CRUD + soft-delete)."""

import pytest

API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY}


class TestProductsList:
    def test_empty_list(self, client):
        resp = client.get("/products/", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_created_products(self, client):
        client.post("/products/", headers=HEADERS, json={"name": "Мёд липовый", "price": 350.0})
        client.post("/products/", headers=HEADERS, json={"name": "Мёд гречишный", "price": 400.0})
        resp = client.get("/products/", headers=HEADERS)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestProductCreate:
    def test_create_minimal(self, client):
        resp = client.post("/products/", headers=HEADERS, json={"name": "Прополис"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Прополис"
        assert data["price"] == 0.0
        assert data["active"] is True
        assert data["id"] > 0

    def test_create_full(self, client):
        resp = client.post("/products/", headers=HEADERS, json={
            "name": "Воск пчелиный",
            "price": 150.0,
            "category": "Продукты пчеловодства",
            "stock": 25,
            "description": "Натуральный воск",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["price"] == 150.0
        assert data["category"] == "Продукты пчеловодства"

    def test_create_requires_name(self, client):
        resp = client.post("/products/", headers=HEADERS, json={"price": 100.0})
        assert resp.status_code == 422


class TestProductGetUpdate:
    def test_get_existing(self, client):
        created = client.post("/products/", headers=HEADERS, json={"name": "Перга", "price": 500.0})
        pid = created.json()["id"]
        resp = client.get(f"/products/{pid}", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Перга"

    def test_get_nonexistent(self, client):
        resp = client.get("/products/99999", headers=HEADERS)
        assert resp.status_code == 404

    def test_update_price(self, client):
        created = client.post("/products/", headers=HEADERS, json={"name": "Пыльца", "price": 200.0})
        pid = created.json()["id"]
        resp = client.patch(f"/products/{pid}", headers=HEADERS, json={"price": 250.0})
        assert resp.status_code == 200
        assert resp.json()["price"] == 250.0


class TestProductSoftDelete:
    def test_soft_delete_sets_active_false(self, client):
        created = client.post("/products/", headers=HEADERS, json={"name": "Маточное молочко"})
        pid = created.json()["id"]
        resp = client.delete(f"/products/{pid}", headers=HEADERS)
        assert resp.status_code == 204
        # После soft-delete объект существует, но active=False
        get_resp = client.get(f"/products/{pid}", headers=HEADERS)
        assert get_resp.status_code == 200
        assert get_resp.json()["active"] is False

    def test_delete_nonexistent(self, client):
        resp = client.delete("/products/99999", headers=HEADERS)
        assert resp.status_code == 404
