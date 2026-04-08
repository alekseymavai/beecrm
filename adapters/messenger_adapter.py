"""MessengerAdapter — нормализация заказов из Telegram / WhatsApp."""

from adapters.base import BaseAdapter


class MessengerAdapter(BaseAdapter):
    def _extract(self, raw: dict) -> dict:
        return {
            "messenger": raw.get("messenger", "telegram"),
            "chat_id": raw.get("chat_id") or raw.get("chatId"),
            "username": raw.get("username"),
            "message": raw.get("message") or raw.get("text"),
            "items": raw.get("items", []),
            "comment": raw.get("comment"),
        }
