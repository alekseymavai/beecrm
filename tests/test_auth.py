"""test_auth.py — тесты аутентификации API (X-API-Key).

Покрытие:
- 403 без заголовка X-API-Key       → уже есть в test_api_from_source.py (test_no_api_key_returns_403)
- 403 с неверным ключом             → test_wrong_api_key_returns_403  [новый]
- 200 с верным ключом на GET /clients/ → test_valid_api_key_allows_access [новый]

Используем фикстуру client из conftest.py (TestClient + FakeIntegramClient).
"""

import os

API_KEY = os.environ.get("API_KEY", "test-api-key")


class TestApiKeyAuth:
    def test_wrong_api_key_returns_403(self, client):
        """Неверный ключ → 403, тело содержит сообщение об ошибке."""
        resp = client.get("/clients/", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 403
        assert "detail" in resp.json()

    def test_valid_api_key_allows_access(self, client):
        """Верный ключ → не 403 (эндпоинт отвечает, аутентификация пройдена)."""
        resp = client.get("/clients/", headers={"X-API-Key": API_KEY})
        assert resp.status_code != 403
