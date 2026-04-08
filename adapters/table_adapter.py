"""TableAdapter — нормализация заказов из Google/Excel таблицы.

openpyxl: read_only=True, data_only=True (только значения, без формул).
"""

from __future__ import annotations

from adapters.base import BaseAdapter


class TableAdapter(BaseAdapter):
    def _extract(self, raw: dict) -> dict:
        return {
            "row": raw.get("row"),
            "sheet": raw.get("sheet"),
            "items": raw.get("items", []),
            "comment": raw.get("comment"),
            "source_channel": raw.get("source_channel"),  # ВК / Instagram / личное
            "manager": raw.get("manager"),
        }

    @classmethod
    def from_xlsx_row(cls, row: dict) -> dict:
        """Принять строку из openpyxl (dict колонка→значение) и нормализовать."""
        adapter = cls()
        return adapter.normalize(row)
