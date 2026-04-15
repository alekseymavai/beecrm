"""test_auth_users.py — тесты JWT login/register."""
import asyncio
import os

import bcrypt
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-key-32-chars-minimum!!")


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


class TestRegister:
    def test_register_creates_user_and_returns_token(self, client, igm):
        resp = client.post("/auth/register", json={"login": "alice", "password": "pass123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == "alice"
        assert data["token_type"] == "bearer"

    def test_register_duplicate_login_returns_409(self, client, igm):
        client.post("/auth/register", json={"login": "bob", "password": "pass"})
        resp = client.post("/auth/register", json={"login": "bob", "password": "pass"})
        assert resp.status_code == 409

    def test_register_short_password_returns_422(self, client):
        resp = client.post("/auth/register", json={"login": "carol", "password": "ab"})
        assert resp.status_code == 422

    def test_register_empty_login_returns_422(self, client):
        resp = client.post("/auth/register", json={"login": "", "password": "pass123"})
        assert resp.status_code == 422


class TestLogin:
    def _seed_user(self, igm, login="dave", password="secret"):
        hashed = _hash(password)
        asyncio.get_event_loop().run_until_complete(
            igm.create_object(
                typeId=igm.T_USERS,
                value=login,
                requisites={
                    str(igm.COL_USER_LOGIN): login,
                    str(igm.COL_USER_HASH): hashed,
                    str(igm.COL_USER_ROLE): "Менеджер",
                    str(igm.COL_USER_ACTIVE): True,
                },
            )
        )

    def test_login_returns_token(self, client, igm):
        self._seed_user(igm)
        resp = client.post("/auth/login", json={"login": "dave", "password": "secret"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == "dave"

    def test_login_wrong_password_returns_401(self, client, igm):
        self._seed_user(igm)
        resp = client.post("/auth/login", json={"login": "dave", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user_returns_401(self, client, igm):
        resp = client.post("/auth/login", json={"login": "ghost", "password": "pass"})
        assert resp.status_code == 401

    def test_login_inactive_user_returns_403(self, client, igm):
        hashed = _hash("pass")
        asyncio.get_event_loop().run_until_complete(
            igm.create_object(
                typeId=igm.T_USERS,
                value="inactive",
                requisites={
                    str(igm.COL_USER_LOGIN): "inactive",
                    str(igm.COL_USER_HASH): hashed,
                    str(igm.COL_USER_ROLE): "Менеджер",
                    str(igm.COL_USER_ACTIVE): False,
                },
            )
        )
        resp = client.post("/auth/login", json={"login": "inactive", "password": "pass"})
        assert resp.status_code == 403
