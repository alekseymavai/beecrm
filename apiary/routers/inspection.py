"""apiary/routers/inspection.py — FSM осмотра улья.

Состояния:
  IDLE        → нет активного осмотра
  INSPECTION  → осмотр идёт: принимаем голос/текст, накапливаем записи

Каждое сообщение:
  1. Проверить регистрацию пользователя
  2. Транскрибировать (если голос) / взять текст
  3. Отправить в LLM → dict
  4. Если requires_clarification: переспросить 1 раз, потом is_draft=True
  5. Сохранить запись в Integram
  6. Обновить счётчик сессии в FSMContext
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from apiary import groq_client, integram_apiary
from apiary.config import INTEGRAM_LOGIN, INTEGRAM_PASSWORD, INTEGRAM_WORKSPACE
from apiary.models import InspectionRecord
from integram.client import IntegramClient

logger = logging.getLogger(__name__)
router = Router(name="inspection")


class InspectionState(StatesGroup):
    active = State()


FINISH_BTN = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Завершить осмотр")]],
    resize_keyboard=True,
)

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐝 Начать осмотр")],
        [KeyboardButton(text="📋 Мои записи"), KeyboardButton(text="ℹ️ Помощь")],
    ],
    resize_keyboard=True,
)


async def _get_client() -> IntegramClient:
    return await IntegramClient.authenticate(
        INTEGRAM_LOGIN, INTEGRAM_PASSWORD, workspace=INTEGRAM_WORKSPACE
    )


async def _check_registered(client: IntegramClient, tg_id: str) -> bool:
    user = await integram_apiary.get_user_by_tg_id(client, tg_id)
    return user is not None and user.is_active


# ── Начать осмотр ──────────────────────────────────────────────────────────────

@router.message(F.text == "🐝 Начать осмотр")
async def btn_start_inspection(message: Message, state: FSMContext) -> None:
    tg_id = str(message.from_user.id)
    client = await _get_client()
    try:
        if not await _check_registered(client, tg_id):
            await message.answer("⛔ Нет доступа. Используйте /start для регистрации.")
            return

        session_id = str(uuid.uuid4())
        await state.set_state(InspectionState.active)
        await state.update_data(
            session_id=session_id,
            record_count=0,
            attention_hives=[],
            pending_clarification=False,
            pending_text=None,
        )
        await message.answer(
            "🐝 Осмотр начат. Отправляйте голосовые или текстовые сообщения.\n"
            "Когда закончите — нажмите кнопку.",
            reply_markup=FINISH_BTN,
        )
    finally:
        await client.close()


# ── Завершить осмотр ───────────────────────────────────────────────────────────

@router.message(InspectionState.active, F.text == "✅ Завершить осмотр")
async def btn_finish_inspection(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    count = data.get("record_count", 0)
    attention = data.get("attention_hives", [])

    await state.clear()

    summary = f"✅ Осмотр завершён. Записей сохранено: {count}."
    if attention:
        hives_str = ", ".join(attention)
        summary += f"\n⚠️ Требуют внимания: {hives_str}"
    else:
        summary += "\nВсе ульи в порядке."

    await message.answer(summary, reply_markup=MAIN_MENU)


# ── Обработка голоса ───────────────────────────────────────────────────────────

@router.message(InspectionState.active, F.voice)
async def handle_voice(message: Message, state: FSMContext) -> None:
    tg_id = str(message.from_user.id)
    client = await _get_client()
    try:
        if not await _check_registered(client, tg_id):
            await message.answer("⛔ Нет доступа.")
            return

        # Скачиваем голос
        bot = message.bot
        file = await bot.get_file(message.voice.file_id)
        ogg_bytes = (await bot.download_file(file.file_path)).read()

        await message.answer("🎙 Распознаю голос...")
        text = await groq_client.transcribe(ogg_bytes)

        await _process_text(message, state, client, tg_id, text, raw_text=text)
    finally:
        await client.close()


# ── Обработка текста ───────────────────────────────────────────────────────────

@router.message(InspectionState.active, F.text)
async def handle_text(message: Message, state: FSMContext) -> None:
    tg_id = str(message.from_user.id)

    # Игнорируем служебные кнопки если они попали сюда
    if message.text in ("🐝 Начать осмотр", "✅ Завершить осмотр", "📋 Мои записи", "ℹ️ Помощь"):
        return

    client = await _get_client()
    try:
        if not await _check_registered(client, tg_id):
            await message.answer("⛔ Нет доступа.")
            return

        data = await state.get_data()
        pending = data.get("pending_clarification", False)

        if pending:
            # Это ответ на вопрос уточнения — добавляем к оригинальному тексту
            original_text = data.get("pending_text", "")
            combined = f"{original_text}\nУлей: {message.text}"
            await state.update_data(pending_clarification=False, pending_text=None)
            await _process_text(message, state, client, tg_id, combined, raw_text=combined, force_draft=True)
        else:
            await _process_text(message, state, client, tg_id, message.text, raw_text=message.text)
    finally:
        await client.close()


# ── Внутренняя обработка ───────────────────────────────────────────────────────

async def _process_text(
    message: Message,
    state: FSMContext,
    client: IntegramClient,
    tg_id: str,
    text: str,
    raw_text: str,
    force_draft: bool = False,
) -> None:
    data = await state.get_data()
    session_id: str = data.get("session_id", str(uuid.uuid4()))

    # Получаем контекст последних осмотров (по первому попавшемуся улью из текста)
    last_records = await _fetch_last_records(client, text)

    result = await groq_client.extract_record(text, last_records)

    if result.get("requires_clarification") and not force_draft:
        question = result.get("clarification_question", "Уточните, пожалуйста, улей.")
        await state.update_data(pending_clarification=True, pending_text=text)
        await message.answer(f"❓ {question}")
        return

    # Строим InspectionRecord
    hive_name = result.get("hive_name", "Неизвестный улей")
    record = InspectionRecord(
        hive_name=hive_name,
        inspection_date=_parse_date(result.get("inspection_date")),
        queen_seen=result.get("queen_seen"),
        brood_status=result.get("brood_status"),
        honey_amount=result.get("honey_amount"),
        health_status=result.get("health_status"),
        actions_taken=result.get("actions_taken"),
        notes=result.get("notes"),
        needs_attention=bool(result.get("needs_attention", False)),
        is_draft=force_draft or result.get("requires_clarification", False),
        session_id=session_id,
        raw_text=raw_text,  # хранится, не логируется
    )

    try:
        obj_id = await integram_apiary.create_inspection(client, record, tg_id, session_id)
    except Exception as exc:
        logger.error("create_inspection failed: %s", exc)
        await message.answer("⚠️ Ошибка при сохранении записи. Попробуйте ещё раз.")
        return

    # Обновляем счётчик сессии
    count = data.get("record_count", 0) + 1
    attention = list(data.get("attention_hives", []))
    if record.needs_attention and hive_name not in attention:
        attention.append(hive_name)
    await state.update_data(record_count=count, attention_hives=attention)

    draft_suffix = " (черновик)" if record.is_draft else ""
    attention_suffix = " ⚠️ Требует внимания!" if record.needs_attention else ""
    await message.answer(
        f"✅ Запись #{count} сохранена{draft_suffix}: {hive_name}{attention_suffix}\n"
        f"ID: {obj_id}"
    )


def _parse_date(value: str | None) -> date:
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return date.today()


async def _fetch_last_records(client: IntegramClient, text: str) -> list:
    """Попытаться извлечь имя улья из текста и загрузить последние осмотры."""
    # Быстрый эвристический поиск числа в тексте как имени улья
    import re
    match = re.search(r'\b(\d{1,3})\b', text)
    if match:
        hive_name = match.group(1)
        return await integram_apiary.get_last_inspections(client, hive_name, n=3)
    return []
