"""apiary/tests/conftest.py — фикстуры для тестов BEEBOTLITE."""

from __future__ import annotations

import os
import sys

import pytest

# ── Устанавливаем обязательные env-переменные ДО импорта модуля ─────────────
os.environ.setdefault("BEEBOTLITE_TOKEN", "1234567890:AAFake_token_for_tests")
os.environ.setdefault("GROQ_API_KEY", "gsk_fake_key_for_tests")
os.environ.setdefault("BEEBOTLITE_ADMIN_TG_ID", "999999999")
os.environ.setdefault("INTEGRAM_LOGIN", "test@example.com")
os.environ.setdefault("INTEGRAM_PASSWORD", "testpassword")

# Заглушки для typeId (0 = не задан, тесты мокируют Integram)
os.environ.setdefault("APIARY_T_ROLES", "100")
os.environ.setdefault("APIARY_T_HEALTH", "101")
os.environ.setdefault("APIARY_T_HIVES", "102")
os.environ.setdefault("APIARY_T_USERS", "103")
os.environ.setdefault("APIARY_T_INSPECTIONS", "104")
os.environ.setdefault("APIARY_COL_USER_TG_ID", "200")
os.environ.setdefault("APIARY_COL_USER_USERNAME", "201")
os.environ.setdefault("APIARY_COL_USER_ROLE", "202")
os.environ.setdefault("APIARY_COL_USER_ACTIVE", "203")
os.environ.setdefault("APIARY_COL_HIVE_LOCATION", "210")
os.environ.setdefault("APIARY_COL_HIVE_NOTES", "211")
os.environ.setdefault("APIARY_COL_HIVE_ACTIVE", "212")
os.environ.setdefault("APIARY_COL_INSP_HIVE_ID", "220")
os.environ.setdefault("APIARY_COL_INSP_DATE", "221")
os.environ.setdefault("APIARY_COL_INSP_INSPECTOR_TG_ID", "222")
os.environ.setdefault("APIARY_COL_INSP_QUEEN_SEEN", "223")
os.environ.setdefault("APIARY_COL_INSP_BROOD_STATUS", "224")
os.environ.setdefault("APIARY_COL_INSP_HONEY_AMOUNT", "225")
os.environ.setdefault("APIARY_COL_INSP_HEALTH_STATUS", "226")
os.environ.setdefault("APIARY_COL_INSP_ACTIONS_TAKEN", "227")
os.environ.setdefault("APIARY_COL_INSP_NOTES", "228")
os.environ.setdefault("APIARY_COL_INSP_NEEDS_ATTENTION", "229")
os.environ.setdefault("APIARY_COL_INSP_IS_DRAFT", "230")
os.environ.setdefault("APIARY_COL_INSP_SESSION_ID", "231")
os.environ.setdefault("APIARY_COL_INSP_RAW_TEXT", "232")


class FakeIntegramClient:
    """In-memory заглушка IntegramClient для тестов."""

    def __init__(self) -> None:
        self._store: dict[int, dict] = {}
        self._counter = 1000

    async def find_by_field(self, typeId: int, col_id: int, value: str):
        for obj in self._store.values():
            if obj.get("typeId") != typeId:
                continue
            for req in obj.get("requisites", []):
                if req.get("id") == col_id and req.get("value") == value:
                    return obj
        return None

    async def list_objects(self, typeId: int, page: int = 1, page_size: int = 50, parent_id=None):
        return [o for o in self._store.values() if o.get("typeId") == typeId]

    async def create_object(self, typeId: int, value: str = "", requisites=None, parentId: int = 1):
        obj_id = self._counter
        self._counter += 1
        reqs = []
        if requisites:
            for k, v in requisites.items():
                reqs.append({"id": int(k), "value": v})
        obj = {"id": obj_id, "typeId": typeId, "value": value, "requisites": reqs}
        self._store[obj_id] = obj
        return obj

    async def update_object(self, objId: int, value=None, requisites=None):
        obj = self._store.get(objId, {})
        if value is not None:
            obj["value"] = value
        if requisites:
            existing = {r["id"]: r for r in obj.get("requisites", [])}
            for k, v in requisites.items():
                existing[int(k)] = {"id": int(k), "value": v}
            obj["requisites"] = list(existing.values())
        self._store[objId] = obj
        return obj

    async def close(self):
        pass


@pytest.fixture
def fake_client():
    return FakeIntegramClient()
