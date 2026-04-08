"""BaseAdapter — template method для нормализации сырых данных.

Security: сырые данные физически не могут покинуть слой адаптеров
без прохождения через normalize(). Каждый адаптер реализует _extract().
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from settings import MAX_PAYLOAD_BYTES

# Ключи, запрещённые в payload (потенциально опасные)
_FORBIDDEN_KEYS = frozenset({"__proto__", "constructor", "prototype"})

# Максимальная длина строкового значения в payload
_MAX_STR_LEN = 2048


class AdapterError(Exception):
    pass


class BaseAdapter(ABC):
    """Template method: normalize() → _extract() → _validate()."""

    def normalize(self, raw: dict) -> dict:
        """Принять сырые данные, вернуть безопасный payload."""
        extracted = self._extract(raw)
        return self._validate(extracted)

    @abstractmethod
    def _extract(self, raw: dict) -> dict:
        """Извлечь нужные поля из сырых данных источника."""

    def _validate(self, data: dict) -> dict:
        # Запрещённые ключи
        bad = _FORBIDDEN_KEYS & set(data.keys())
        if bad:
            raise AdapterError(f"Запрещённые ключи в payload: {bad}")

        # Обрезаем длинные строки
        cleaned = {
            k: (v[:_MAX_STR_LEN] if isinstance(v, str) else v)
            for k, v in data.items()
        }

        # Проверка размера
        size = len(json.dumps(cleaned, ensure_ascii=False).encode())
        if size > MAX_PAYLOAD_BYTES:
            raise AdapterError(
                f"payload {size} байт превышает лимит {MAX_PAYLOAD_BYTES}"
            )

        return cleaned
