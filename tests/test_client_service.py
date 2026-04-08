"""test_client_service.py — дедупликация клиентов (fragile zone HIGH)."""

import pytest
from services.client_service import find_or_create


class TestFindOrCreate:
    def test_create_new_by_phone(self, db):
        client, created = find_or_create(db, phone="+79001111111")
        assert created is True
        assert client.id is not None
        assert client.phone == "+79001111111"

    def test_find_existing_by_phone(self, db):
        find_or_create(db, phone="+79002222222", name="Андрей")
        client, created = find_or_create(db, phone="+79002222222")
        assert created is False
        assert client.name == "Андрей"

    def test_find_existing_by_email(self, db):
        find_or_create(db, email="test@example.com", name="Алексей")
        client, created = find_or_create(db, email="test@example.com")
        assert created is False
        assert client.name == "Алексей"

    def test_dedup_phone_takes_priority_over_email(self, db):
        """Один клиент из UDS (phone) и мессенджера (phone) — не дубль."""
        client1, _ = find_or_create(db, phone="+79003333333", email="a@a.com")
        client2, created = find_or_create(db, phone="+79003333333", email="b@b.com")
        assert created is False
        assert client1.id == client2.id

    def test_fill_missing_fields(self, db):
        """Если нашли по phone — дополняем email если его не было."""
        client, _ = find_or_create(db, phone="+79004444444")
        assert client.email is None
        client2, created = find_or_create(db, phone="+79004444444", email="new@email.com")
        assert created is False
        assert client2.email == "new@email.com"

    def test_requires_phone_or_email(self, db):
        with pytest.raises(ValueError, match="phone или email"):
            find_or_create(db)
