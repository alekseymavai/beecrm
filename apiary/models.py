"""apiary/models.py — Pydantic модели данных BEEBOTLITE."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class Hive(BaseModel):
    integram_id: int
    name: str
    location: Optional[str] = None
    is_active: bool = True


class ApiaryUser(BaseModel):
    integram_id: int
    tg_id: str
    tg_username: Optional[str] = None
    role: str = "Пчеловод"
    is_active: bool = True


class InspectionRecord(BaseModel):
    hive_name: str
    inspection_date: date
    queen_seen: Optional[bool] = None
    brood_status: Optional[str] = None
    honey_amount: Optional[str] = None
    health_status: Optional[str] = None   # Здоров / Требует внимания / Болен / Подозрение
    actions_taken: Optional[str] = None
    notes: Optional[str] = None
    needs_attention: bool = False
    is_draft: bool = False
    session_id: Optional[str] = None
    raw_text: Optional[str] = None        # хранится, не логируется
