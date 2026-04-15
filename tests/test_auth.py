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


class TestJwtAuth:
    def test_jwt_allows_access_to_clients(self, client):
        import os
        from datetime import datetime, timedelta, timezone
        from jose import jwt as jose_jwt

        secret = os.environ.get("JWT_SECRET", "test-secret-key-32-chars-minimum!!")
        token = jose_jwt.encode(
            {"sub": "testuser", "role": "Администратор",
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            secret, algorithm="HS256",
        )
        resp = client.get("/clients/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code != 403

    def test_invalid_jwt_returns_403(self, client):
        resp = client.get("/clients/", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 403
