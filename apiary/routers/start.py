"""apiary/routers/start.py — /start, главное меню, регистрация."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from apiary.config import ADMIN_TG_ID, INTEGRAM_LOGIN, INTEGRAM_PASSWORD, INTEGRAM_WORKSPACE
from apiary import integram_apiary
from integram.client import IntegramClient

logger = logging.getLogger(__name__)
router = Router(name="start")

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


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    tg_id = str(message.from_user.id)
    username = message.from_user.username

    client = await _get_client()
    try:
        user = await integram_apiary.get_user_by_tg_id(client, tg_id)

        if user is None:
            # Создаём заявку на регистрацию
            await integram_apiary.create_user(client, tg_id, username)
            await message.answer(
                "👋 Привет! Ваша заявка на доступ отправлена администратору.\n"
                "Ожидайте одобрения — вам придёт уведомление."
            )
            # Уведомить администратора
            try:
                await bot.send_message(
                    ADMIN_TG_ID,
                    f"🔔 Новая заявка на регистрацию:\n"
                    f"tg_id: {tg_id}\n"
                    f"username: @{username or 'нет'}\n\n"
                    f"Одобрить: /approve {tg_id}",
                )
            except Exception as exc:
                logger.warning("Не удалось уведомить администратора: %s", exc)
            return

        if not user.is_active:
            await message.answer(
                "⏳ Ваш аккаунт ещё не одобрен администратором.\n"
                "Ожидайте уведомления."
            )
            return

        await message.answer(
            f"🐝 Добро пожаловать, {message.from_user.first_name}!\n"
            "Выберите действие:",
            reply_markup=MAIN_MENU,
        )
    finally:
        await client.close()
