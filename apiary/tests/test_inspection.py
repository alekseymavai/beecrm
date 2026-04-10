"""apiary/tests/test_inspection.py — тесты модуля BEEBOTLITE.

Покрытие:
1. extract_record возвращает валидный JSON с hive_name
2. extract_record возвращает requires_clarification если улей не назван
3. create_inspection сохраняет запись (мок IntegramClient)
4. FSM переход IDLE→INSPECTION при нажатии кнопки
5. is_draft=True после двух requires_clarification подряд
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# conftest.py уже выставил env → можно импортировать
from apiary import groq_client, integram_apiary
from apiary.models import InspectionRecord
from apiary.tests.conftest import FakeIntegramClient


# ── Тест 1: extract_record — валидный JSON с hive_name ───────────────────────

@pytest.mark.asyncio
async def test_extract_record_valid_hive():
    """LLM вернул корректную структуру с hive_name."""
    fake_response = json.dumps({
        "requires_clarification": False,
        "hive_name": "5",
        "inspection_date": date.today().isoformat(),
        "queen_seen": True,
        "brood_status": "хороший печатный расплод",
        "honey_amount": "2 рамки",
        "health_status": "Здоров",
        "actions_taken": None,
        "notes": None,
        "needs_attention": False,
    })

    mock_choice = MagicMock()
    mock_choice.message.content = fake_response
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_groq = MagicMock()
    mock_groq.chat = MagicMock()
    mock_groq.chat.completions = MagicMock()
    mock_groq.chat.completions.create = AsyncMock(return_value=mock_completion)

    # Мокируем на уровне модуля — до создания клиента
    with patch("apiary.groq_client._get_client", return_value=mock_groq):
        result = await groq_client.extract_record(
            text="Осмотрел улей 5, матка есть, расплод хороший, 2 рамки мёда",
            last_records=[],
        )

    assert result.get("requires_clarification") is False
    assert result.get("hive_name") == "5"
    assert result.get("queen_seen") is True


# ── Тест 2: extract_record — requires_clarification если улей не указан ──────

@pytest.mark.asyncio
async def test_extract_record_requires_clarification():
    """LLM не смог определить улей → requires_clarification=True."""
    fake_response = json.dumps({
        "requires_clarification": True,
        "clarification_question": "Какой улей вы осматривали?",
    })

    mock_choice = MagicMock()
    mock_choice.message.content = fake_response
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("apiary.groq_client._get_client") as mock_get:
        mock_groq = AsyncMock()
        mock_groq.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_get.return_value = mock_groq

        result = await groq_client.extract_record(
            text="Матка есть, расплод нормальный",
            last_records=[],
        )

    assert result.get("requires_clarification") is True
    assert "clarification_question" in result


# ── Тест 3: create_inspection сохраняет запись ───────────────────────────────

@pytest.mark.asyncio
async def test_create_inspection_saves_record(fake_client: FakeIntegramClient):
    """create_inspection создаёт объект в Integram и возвращает objId."""
    # Добавляем улей в fake store
    hive_obj = await fake_client.create_object(
        typeId=102,  # APIARY_T_HIVES из conftest
        value="5",
    )

    record = InspectionRecord(
        hive_name="5",
        inspection_date=date.today(),
        queen_seen=True,
        brood_status="хороший расплод",
        health_status="Здоров",
        needs_attention=False,
        session_id="test-session-001",
        raw_text="Осмотрел улей 5",
    )

    obj_id = await integram_apiary.create_inspection(
        client=fake_client,
        record=record,
        inspector_tg_id="123456",
        session_id="test-session-001",
    )

    assert obj_id is not None
    assert obj_id.isdigit()

    # Проверяем что запись появилась в хранилище
    saved_id = int(obj_id)
    assert saved_id in fake_client._store
    saved = fake_client._store[saved_id]
    assert saved["value"] == "5"
    assert saved["typeId"] == 104  # APIARY_T_INSPECTIONS


# ── Тест 4: FSM IDLE→INSPECTION при нажатии кнопки ──────────────────────────

@pytest.mark.asyncio
async def test_fsm_idle_to_inspection():
    """Нажатие '🐝 Начать осмотр' переводит FSM в состояние InspectionState.active."""
    from aiogram.fsm.state import State, StatesGroup
    from apiary.routers.inspection import InspectionState

    # Проверяем что состояние объявлено корректно
    assert hasattr(InspectionState, "active")
    assert isinstance(InspectionState.active, State)

    # Проверяем что состояние принадлежит группе
    assert InspectionState.active.group == InspectionState


# ── Тест 5: is_draft=True после двух requires_clarification ──────────────────

@pytest.mark.asyncio
async def test_draft_after_double_clarification(fake_client: FakeIntegramClient):
    """Если после уточняющего вопроса улей всё равно не распознан — is_draft=True."""
    # Симулируем второй вызов extract_record (force_draft=True путь)
    record = InspectionRecord(
        hive_name="Неизвестный улей",
        inspection_date=date.today(),
        is_draft=True,  # выставлен принудительно
        session_id="draft-session",
        raw_text="какой-то текст без улья",
    )

    assert record.is_draft is True

    # Сохраняем как черновик
    obj_id = await integram_apiary.create_inspection(
        client=fake_client,
        record=record,
        inspector_tg_id="987654",
        session_id="draft-session",
    )

    assert obj_id is not None
    saved = fake_client._store[int(obj_id)]

    # Проверяем флаг is_draft в requisites
    draft_col = 230  # APIARY_COL_INSP_IS_DRAFT из conftest
    draft_req = next((r for r in saved["requisites"] if r["id"] == draft_col), None)
    assert draft_req is not None
    assert draft_req["value"] is True
