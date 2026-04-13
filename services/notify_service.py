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

    def __init__(
        self,
        bot: "Bot",
        igm: "IntegramClient",
        admin_tg_id: int = 0,
        recipient_provider=None,
    ) -> None:
        self._bot = bot
        self._igm = igm
        self._admin_tg_id = admin_tg_id
        # async callable (client: IntegramClient) -> list[int]
        self._recipient_provider = recipient_provider

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
        """Получить список chat_id активных пользователей."""
        if self._recipient_provider is not None:
            try:
                recipients = await self._recipient_provider(self._igm)
                if recipients:
                    return recipients
            except Exception as exc:  # noqa: BLE001
                logger.warning("_get_recipients: ошибка провайдера: %s — fallback на admin", exc)
        return [self._admin_tg_id] if self._admin_tg_id else []

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
