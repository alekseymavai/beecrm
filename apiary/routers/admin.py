"""apiary/routers/admin.py — административные команды BEEBOTLITE.

Только ADMIN_TG_ID может использовать эти команды.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from apiary import integram_apiary
from apiary.config import ADMIN_TG_ID, INTEGRAM_LOGIN, INTEGRAM_PASSWORD, INTEGRAM_WORKSPACE
from integram.client import IntegramClient

logger = logging.getLogger(__name__)
router = Router(name="admin")


async def _get_client() -> IntegramClient:
    return await IntegramClient.authenticate(
        INTEGRAM_LOGIN, INTEGRAM_PASSWORD, workspace=INTEGRAM_WORKSPACE
    )


def _is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_TG_ID


# ── /adduser ──────────────────────────────────────────────────────────────────

@router.message(Command("adduser"))
async def cmd_adduser(message: Message) -> None:
    """Синтаксис: /adduser <tg_id> [роль]"""
    if not _is_admin(message):
        await message.answer("⛔ Нет прав.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Использование: /adduser <tg_id> [роль]\nПример: /adduser 123456789 Пчеловод")
        return

    tg_id = parts[1]
    role = parts[2] if len(parts) > 2 else "Пчеловод"

    client = await _get_client()
    try:
        existing = await integram_apiary.get_user_by_tg_id(client, tg_id)
        if existing:
            await message.answer(f"⚠️ Пользователь {tg_id} уже существует (роль: {existing.role}).")
            return

        user = await integram_apiary.create_user(client, tg_id, role=role)
        # Сразу одобряем
        await integram_apiary.approve_user(client, tg_id)
        await message.answer(f"✅ Пользователь {tg_id} создан и одобрен.\nРоль: {role}")
    finally:
        await client.close()


# ── /approve ──────────────────────────────────────────────────────────────────

@router.message(Command("approve"))
async def cmd_approve(message: Message) -> None:
    """Синтаксис: /approve <tg_id>"""
    if not _is_admin(message):
        await message.answer("⛔ Нет прав.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Использование: /approve <tg_id>")
        return

    tg_id = parts[1]
    client = await _get_client()
    try:
        ok = await integram_apiary.approve_user(client, tg_id)
        if ok:
            await message.answer(f"✅ Пользователь {tg_id} одобрен.")
            # Уведомить пользователя
            try:
                await message.bot.send_message(
                    int(tg_id),
                    "🎉 Ваш аккаунт одобрен! Нажмите /start для начала работы.",
                )
            except Exception as exc:
                logger.warning("Не удалось уведомить пользователя %s: %s", tg_id, exc)
        else:
            await message.answer(f"⚠️ Пользователь {tg_id} не найден.")
    finally:
        await client.close()


# ── /addhive ──────────────────────────────────────────────────────────────────

@router.message(Command("addhive"))
async def cmd_addhive(message: Message) -> None:
    """Синтаксис: /addhive <name> [location]"""
    if not _is_admin(message):
        await message.answer("⛔ Нет прав.")
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Использование: /addhive <имя> [расположение]\nПример: /addhive 5 Северный сад")
        return

    name = parts[1]
    location = parts[2] if len(parts) > 2 else None

    client = await _get_client()
    try:
        existing = await integram_apiary.get_hive_by_name(client, name)
        if existing:
            await message.answer(f"⚠️ Улей '{name}' уже существует (ID: {existing.integram_id}).")
            return

        hive = await integram_apiary.create_hive(client, name, location)
        loc_str = f"\nРасположение: {location}" if location else ""
        await message.answer(f"✅ Улей '{name}' создан (ID: {hive.integram_id}).{loc_str}")
    finally:
        await client.close()
