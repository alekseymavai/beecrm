"""services/notify_service.py — уведомления команде пчеловода о новых заказах.

Отправляет Telegram-сообщение всем активным пользователям BEEBOTLITE
при появлении нового заказа из UDS.
Ошибка отправки НЕ прерывает обработку заказа.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram import Bot
    from integram.client import IntegramClient

logger = logging.getLogger(__name__)


class NotifyService:
    """Рассылка Telegram-уведомлений команде пчеловода."""

    def __init__(self, bot: "Bot", igm: "IntegramClient", admin_tg_id: int = 0) -> None:
        self._bot = bot
        self._igm = igm
        self._admin_tg_id = admin_tg_id

    async def notify_new_order(self, parsed: dict) -> None:
        """Отправить уведомление о новом UDS-заказе всем активным пользователям.

        Ошибки отправки поглощаются — не прерывают обработку заказа.
        """
        try:
            recipients = await self._get_recipients()
            if not recipients:
                logger.warning("notify_new_order: нет получателей — уведомление не отправлено")
                return
            text = _format_message(parsed)
            for chat_id in recipients:
                await self._send(chat_id, text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("notify_new_order: ошибка рассылки: %s", exc)

    async def _get_recipients(self) -> list[int]:
        """Получить список chat_id активных пользователей.

        Источник: Integram APIARY_T_USERS (если настроен) или ADMIN_TG_ID.
        chat_id берётся только из доверенного источника — Integram или env.
        """
        # Импортируем здесь, чтобы не тянуть apiary-зависимости в uds/ напрямую
        try:
            from apiary import config as apiary_config
        except ImportError:
            logger.warning("_get_recipients: модуль apiary недоступен — fallback на admin")
            return [self._admin_tg_id] if self._admin_tg_id else []

        if not apiary_config.APIARY_T_USERS or not apiary_config.COL_USER_TG_ID:
            # Таблица пользователей не настроена — только admin
            if self._admin_tg_id:
                return [self._admin_tg_id]
            return []

        try:
            rows = await self._igm.list_objects(apiary_config.APIARY_T_USERS, page_size=200)
        except Exception as exc:  # noqa: BLE001
            logger.warning("_get_recipients: ошибка запроса к Integram: %s — fallback на admin", exc)
            return [self._admin_tg_id] if self._admin_tg_id else []

        recipients: list[int] = []
        for row in rows:
            # Получаем полный объект, чтобы иметь requisites
            try:
                full = await self._igm.get_object(row["id"])
                if full is None:
                    continue
                reqs = full.get("requisites", {})
                is_active = reqs.get(str(apiary_config.COL_USER_ACTIVE))
                if not is_active:
                    continue
                tg_id_raw = reqs.get(str(apiary_config.COL_USER_TG_ID))
                if tg_id_raw:
                    try:
                        recipients.append(int(tg_id_raw))
                    except (ValueError, TypeError):
                        logger.warning("_get_recipients: невалидный tg_id=%r — пропуск", tg_id_raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning("_get_recipients: ошибка при обработке записи %s: %s", row.get("id"), exc)

        if not recipients and self._admin_tg_id:
            return [self._admin_tg_id]
        return recipients

    async def _send(self, chat_id: int, text: str) -> None:
        """Отправить сообщение в один чат. Ошибка логируется без sensitive данных."""
        try:
            await self._bot.send_message(chat_id=chat_id, text=text)
        except Exception as exc:  # noqa: BLE001
            # Не логируем chat_id и текст — только тип ошибки
            logger.warning("_send: не удалось отправить уведомление (chat_id=***): %s", type(exc).__name__)


def _format_message(parsed: dict) -> str:
    """Сформировать текст уведомления о новом UDS-заказе."""
    name = parsed.get("customer_name") or "—"
    phone = parsed.get("customer_phone") or "—"
    total = parsed.get("total")

    lines = [
        "🛒 Новый заказ UDS",
        f"Клиент: {name}",
        f"Тел: {phone}",
    ]
    if total is not None:
        lines.append(f"Сумма: {total} ₽")

    return "\n".join(lines)
