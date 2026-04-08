"""test_client_service.py — дедупликация клиентов (fragile zone HIGH)."""

import pytest
from services.client_service import find_or_create


class TestFindOrCreate:
    async def test_create_new_by_phone(self, igm):
        client, created = await find_or_create(igm, phone="+79001111111")
        assert created is True
        assert client["id"] is not None
        assert client["phone"] == "+79001111111"

    async def test_find_existing_by_phone(self, igm):
        await find_or_create(igm, phone="+79002222222", name="Андрей")
        client, created = await find_or_create(igm, phone="+79002222222")
        assert created is False
        assert client["name"] == "Андрей"

    async def test_find_existing_by_email(self, igm):
        await find_or_create(igm, email="test@example.com", name="Алексей")
        client, created = await find_or_create(igm, email="test@example.com")
        assert created is False
        assert client["name"] == "Алексей"

    async def test_dedup_phone_takes_priority_over_email(self, igm):
        """Один клиент из UDS (phone) и мессенджера (phone) — не дубль."""
        client1, _ = await find_or_create(igm, phone="+79003333333", email="a@a.com")
        client2, created = await find_or_create(igm, phone="+79003333333", email="b@b.com")
        assert created is False
        assert client1["id"] == client2["id"]

    async def test_fill_missing_fields(self, igm):
        """Если нашли по phone — дополняем email если его не было."""
        client, _ = await find_or_create(igm, phone="+79004444444")
        assert client.get("email") is None
        client2, created = await find_or_create(igm, phone="+79004444444", email="new@email.com")
        assert created is False
        assert client2["email"] == "new@email.com"

    async def test_requires_phone_or_email(self, igm):
        with pytest.raises(ValueError, match="phone или email"):
            await find_or_create(igm)
