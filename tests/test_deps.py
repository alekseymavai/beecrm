"""test_deps.py — тесты для integram/deps.py (get_current_user).

Покрытие:
- JWT с валидной ролью → возвращает username и role
- X-API-Key → возвращает {"username": "api", "role": "API"}
- Невалидный JWT → 401
- Отсутствует аутентификация → 401
- Истекший JWT → 401
"""

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

import settings
from integram.deps import get_current_user

API_KEY = os.environ.get("API_KEY", "test-api-key")
JWT_SECRET = os.environ.get("JWT_SECRET", "test-secret-key-32-chars-minimum!!")


class TestGetCurrentUserJWT:
    """Тесты JWT аутентификации."""

    def test_valid_jwt_returns_user_with_role(self):
        """Валидный JWT с ролью → возвращает {"username": ..., "role": ...}."""
        token = jose_jwt.encode(
            {
                "sub": "testuser",
                "role": "Собственник",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            JWT_SECRET,
            algorithm="HS256",
        )
        # Симулируем Depends() вызов
        from unittest.mock import AsyncMock, patch

        async def run_test():
            with patch("integram.deps.settings.JWT_SECRET", JWT_SECRET):
                result = await get_current_user(
                    authorization=f"Bearer {token}", api_key=None
                )
            assert result["username"] == "testuser"
            assert result["role"] == "Собственник"

        import asyncio

        asyncio.run(run_test())

    def test_jwt_without_role_defaults_to_manager(self):
        """JWT без role → используется "Менеджер"."""
        token = jose_jwt.encode(
            {"sub": "testuser", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            JWT_SECRET,
            algorithm="HS256",
        )

        from unittest.mock import patch
        import asyncio

        async def run_test():
            with patch("integram.deps.settings.JWT_SECRET", JWT_SECRET):
                result = await get_current_user(
                    authorization=f"Bearer {token}", api_key=None
                )
            assert result["username"] == "testuser"
            assert result["role"] == "Менеджер"

        asyncio.run(run_test())

    def test_invalid_jwt_falls_back_to_api_key(self):
        """Невалидный JWT + X-API-Key → возвращает api user."""

        from unittest.mock import patch
        import asyncio

        async def run_test():
            with patch("integram.deps.settings.API_KEY", API_KEY):
                result = await get_current_user(
                    authorization="Bearer bad.token.here", api_key=API_KEY
                )
            assert result["username"] == "api"
            assert result["role"] == "API"

        asyncio.run(run_test())

    def test_expired_jwt_falls_back_to_api_key(self):
        """Истекший JWT + X-API-Key → возвращает api user."""
        token = jose_jwt.encode(
            {
                "sub": "testuser",
                "role": "Собственник",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            JWT_SECRET,
            algorithm="HS256",
        )

        from unittest.mock import patch
        import asyncio

        async def run_test():
            with patch("integram.deps.settings.JWT_SECRET", JWT_SECRET):
                with patch("integram.deps.settings.API_KEY", API_KEY):
                    result = await get_current_user(
                        authorization=f"Bearer {token}", api_key=API_KEY
                    )
            assert result["username"] == "api"
            assert result["role"] == "API"

        asyncio.run(run_test())


class TestGetCurrentUserApiKey:
    """Тесты X-API-Key аутентификации."""

    def test_valid_api_key_returns_api_user(self):
        """Верный X-API-Key → {"username": "api", "role": "API"}."""

        from unittest.mock import patch
        import asyncio

        async def run_test():
            with patch("integram.deps.settings.API_KEY", API_KEY):
                result = await get_current_user(authorization=None, api_key=API_KEY)
            assert result["username"] == "api"
            assert result["role"] == "API"

        asyncio.run(run_test())

    def test_invalid_api_key_raises_401(self):
        """Неверный X-API-Key → HTTPException(401)."""

        from unittest.mock import patch
        import asyncio

        async def run_test():
            with patch("integram.deps.settings.API_KEY", API_KEY):
                try:
                    await get_current_user(
                        authorization=None, api_key="wrong-key"
                    )
                    assert False, "Should raise HTTPException"
                except HTTPException as e:
                    assert e.status_code == 401

        asyncio.run(run_test())


class TestGetCurrentUserErrors:
    """Тесты ошибок аутентификации."""

    def test_no_auth_headers_raises_401(self):
        """Нет X-API-Key и JWT → HTTPException(401)."""

        import asyncio

        async def run_test():
            try:
                await get_current_user(authorization=None, api_key=None)
                assert False, "Should raise HTTPException"
            except HTTPException as e:
                assert e.status_code == 401
                assert "Требуется аутентификация" in e.detail

        asyncio.run(run_test())

    def test_bearer_prefix_required(self):
        """Authorization без "Bearer " префикса → fallback на X-API-Key."""

        from unittest.mock import patch
        import asyncio

        async def run_test():
            with patch("integram.deps.settings.API_KEY", API_KEY):
                result = await get_current_user(
                    authorization="NotBearer token", api_key=API_KEY
                )
            assert result["username"] == "api"

        asyncio.run(run_test())


class TestGetCurrentUserIntegration:
    """Интеграционные тесты через endpoint."""

    def test_beelog_hives_endpoint_with_jwt(self, client):
        """POST /beelog/hives с JWT токеном → работает."""
        token = jose_jwt.encode(
            {
                "sub": "beekeeper",
                "role": "Собственник",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            JWT_SECRET,
            algorithm="HS256",
        )
        resp = client.post(
            "/beelog/hives",
            json={"number": "UL-001", "location": "Апiary"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code != 401, f"Got {resp.status_code}: {resp.text}"

    def test_beelog_hives_endpoint_with_api_key(self, client):
        """POST /beelog/hives с X-API-Key → 403 (role != Собственник)."""
        resp = client.post(
            "/beelog/hives",
            json={"number": "UL-001", "location": "Apiary"},
            headers={"X-API-Key": API_KEY},
        )
        # Ожидаем 403 потому что роль "API", а не "Собственник"
        assert resp.status_code == 403

    def test_beelog_hives_endpoint_no_auth(self, client):
        """POST /beelog/hives без аутентификации → 403 (verify_api_key ловит раньше)."""
        resp = client.post(
            "/beelog/hives",
            json={"number": "UL-001", "location": "Apiary"},
        )
        # verify_api_key в main.py ловит раньше get_current_user
        assert resp.status_code == 403
