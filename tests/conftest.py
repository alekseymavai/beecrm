"""conftest.py — фикстуры для тестов (FakeIntegramClient)."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("INTEGRAM_LOGIN", "test-login")
os.environ.setdefault("INTEGRAM_PASSWORD", "test-password")

from integram.deps import get_integram  # noqa: E402
from main import app  # noqa: E402
from tests.mocks.integram_mock import FakeIntegramClient  # noqa: E402


@pytest.fixture
def igm():
    return FakeIntegramClient()


@pytest.fixture
def client(igm):
    app.dependency_overrides[get_integram] = lambda: igm
    with patch("main.IntegramClient.authenticate", new=AsyncMock(return_value=igm)):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()
