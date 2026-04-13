"""apiary/integram_apiary.py — методы доступа к Integram для модуля BEEBOTLITE.

TypeId таблиц задаются через env-переменные APIARY_T_* (см. apiary/config.py).
Запустить apiary/scripts/create_tables.py один раз для создания таблиц,
затем прописать полученные typeId в .env.
"""

from __future__ import annotations

import logging
from typing import Any

from integram.client import IntegramClient
from integram.exceptions import IntegramError

from apiary import config
from apiary.models import ApiaryUser, Hive, InspectionRecord

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _reqs(**kwargs: Any) -> dict[str, Any]:
    """Собрать requisites, пропустив нулевые col_id и None-значения."""
    return {str(k): v for k, v in kwargs.items() if k and v is not None}


def _row_value(row: dict, col_id: int) -> Any:
    """Извлечь значение поля по col_id из Integram-объекта.

    Integram v2 возвращает requisites как dict {"colId": value},
    list_objects возвращает объекты без requisites — нужен get_object.
    """
    reqs = row.get("requisites", {})
    if isinstance(reqs, dict):
        return reqs.get(str(col_id))
    # Старый формат (массив) — на случай совместимости
    for req in reqs:
        if req.get("id") == col_id:
            return req.get("value")
    return None


# ── Users ─────────────────────────────────────────────────────────────────────

async def get_user_by_tg_id(client: IntegramClient, tg_id: str) -> ApiaryUser | None:
    """Найти пользователя бота по Telegram ID."""
    if not config.APIARY_T_USERS or not config.COL_USER_TG_ID:
        logger.warning("get_user_by_tg_id: APIARY_T_USERS или COL_USER_TG_ID не задан")
        return None
    try:
        row = await client.find_by_field(
            config.APIARY_T_USERS,
            config.COL_USER_TG_ID,
            tg_id,
        )
        if row is None:
            return None
        # list_objects не включает requisites — получаем полный объект
        full = await client.get_object(row["id"])
        if full is None:
            return None
        return ApiaryUser(
            integram_id=full["id"],
            tg_id=tg_id,
            tg_username=_row_value(full, config.COL_USER_USERNAME),
            role=_row_value(full, config.COL_USER_ROLE) or "Пчеловод",
            is_active=bool(_row_value(full, config.COL_USER_ACTIVE)),
        )
    except IntegramError as exc:
        logger.error("get_user_by_tg_id(%s): %s", tg_id, exc)
        return None


async def create_user(
    client: IntegramClient,
    tg_id: str,
    username: str | None = None,
    role: str = "Пчеловод",
) -> ApiaryUser:
    """Создать нового пользователя бота."""
    obj = await client.create_object(
        config.APIARY_T_USERS,
        value=username or tg_id,
        requisites=_reqs(**{
            str(config.COL_USER_TG_ID): tg_id,
            str(config.COL_USER_USERNAME): username,
            str(config.COL_USER_ACTIVE): False,  # ждёт одобрения
        }),
    )
    return ApiaryUser(
        integram_id=obj["id"],
        tg_id=tg_id,
        tg_username=username,
        role=role,
        is_active=False,
    )


async def approve_user(client: IntegramClient, tg_id: str) -> bool:
    """Одобрить пользователя (is_active=True)."""
    user = await get_user_by_tg_id(client, tg_id)
    if user is None:
        return False
    await client.update_object(
        user.integram_id,
        requisites={str(config.COL_USER_ACTIVE): True},
    )
    return True


# ── Hives ─────────────────────────────────────────────────────────────────────

async def get_hive_by_name(client: IntegramClient, name: str) -> Hive | None:
    """Найти улей по имени (value в Integram)."""
    if not config.APIARY_T_HIVES:
        logger.warning("get_hive_by_name: APIARY_T_HIVES не задан")
        return None
    try:
        rows = await client.list_objects(config.APIARY_T_HIVES, page_size=100)
        for row in rows:
            if row.get("value", "").strip().lower() == name.strip().lower():
                return Hive(
                    integram_id=row["id"],
                    name=row.get("value", name),
                    location=_row_value(row, config.COL_HIVE_LOCATION),
                    is_active=bool(_row_value(row, config.COL_HIVE_ACTIVE) if config.COL_HIVE_ACTIVE else True),
                )
        return None
    except IntegramError as exc:
        logger.error("get_hive_by_name(%s): %s", name, exc)
        return None


async def create_hive(
    client: IntegramClient,
    name: str,
    location: str | None = None,
) -> Hive:
    """Создать новый улей."""
    obj = await client.create_object(
        config.APIARY_T_HIVES,
        value=name,
        requisites=_reqs(**{
            str(config.COL_HIVE_LOCATION): location,
            str(config.COL_HIVE_ACTIVE): True,
        }),
    )
    return Hive(integram_id=obj["id"], name=name, location=location)


# ── Inspections ───────────────────────────────────────────────────────────────

async def create_inspection(
    client: IntegramClient,
    record: InspectionRecord,
    inspector_tg_id: str,
    session_id: str,
) -> str:
    """Сохранить запись осмотра. Возвращает objId созданной записи."""
    hive = await get_hive_by_name(client, record.hive_name)
    hive_id = hive.integram_id if hive else None

    # Найти objId статуса здоровья в справочнике (по имени)
    health_status_id: int | None = None
    if record.health_status and config.APIARY_T_HEALTH:
        try:
            health_rows = await client.list_objects(config.APIARY_T_HEALTH, page_size=20)
            for h in health_rows:
                if h.get("value", "") == record.health_status:
                    health_status_id = h["id"]
                    break
        except IntegramError:
            pass

    reqs: dict[str, Any] = {}
    if hive_id and config.COL_INSP_HIVE_ID:
        reqs[str(config.COL_INSP_HIVE_ID)] = hive_id
    if config.COL_INSP_DATE:
        reqs[str(config.COL_INSP_DATE)] = record.inspection_date.isoformat()
    if config.COL_INSP_INSPECTOR_TG_ID:
        reqs[str(config.COL_INSP_INSPECTOR_TG_ID)] = inspector_tg_id
    if record.queen_seen is not None and config.COL_INSP_QUEEN_SEEN:
        reqs[str(config.COL_INSP_QUEEN_SEEN)] = record.queen_seen
    if record.brood_status and config.COL_INSP_BROOD_STATUS:
        reqs[str(config.COL_INSP_BROOD_STATUS)] = record.brood_status
    if record.honey_amount and config.COL_INSP_HONEY_AMOUNT:
        reqs[str(config.COL_INSP_HONEY_AMOUNT)] = record.honey_amount
    if health_status_id and config.COL_INSP_HEALTH_STATUS:
        reqs[str(config.COL_INSP_HEALTH_STATUS)] = health_status_id
    if record.actions_taken and config.COL_INSP_ACTIONS_TAKEN:
        reqs[str(config.COL_INSP_ACTIONS_TAKEN)] = record.actions_taken
    if record.notes and config.COL_INSP_NOTES:
        reqs[str(config.COL_INSP_NOTES)] = record.notes
    if config.COL_INSP_NEEDS_ATTENTION:
        reqs[str(config.COL_INSP_NEEDS_ATTENTION)] = record.needs_attention
    if config.COL_INSP_IS_DRAFT:
        reqs[str(config.COL_INSP_IS_DRAFT)] = record.is_draft
    if config.COL_INSP_SESSION_ID:
        reqs[str(config.COL_INSP_SESSION_ID)] = session_id
    if record.raw_text and config.COL_INSP_RAW_TEXT:
        # raw_text хранится, не логируется
        reqs[str(config.COL_INSP_RAW_TEXT)] = record.raw_text

    obj = await client.create_object(
        config.APIARY_T_INSPECTIONS,
        value=record.hive_name,
        requisites=reqs,
    )
    return str(obj["id"])


async def get_last_inspections(
    client: IntegramClient,
    hive_name: str,
    n: int = 3,
) -> list[dict]:
    """Получить последние n осмотров улья по имени."""
    if not config.APIARY_T_INSPECTIONS:
        return []
    try:
        hive = await get_hive_by_name(client, hive_name)
        if hive is None:
            return []
        rows = await client.list_objects(config.APIARY_T_INSPECTIONS, page_size=50)
        hive_rows = [
            r for r in rows
            if _row_value(r, config.COL_INSP_HIVE_ID) == hive.integram_id
        ]
        # сортируем по id desc (последние первые)
        hive_rows.sort(key=lambda r: r.get("id", 0), reverse=True)
        return hive_rows[:n]
    except IntegramError as exc:
        logger.error("get_last_inspections(%s): %s", hive_name, exc)
        return []


# ── Notify helpers ────────────────────────────────────────────────────────────

async def get_active_user_tg_ids(client: IntegramClient) -> list[int]:
    """Получить tg_id всех активных пользователей бота. При ошибке — пустой список."""
    if not config.APIARY_T_USERS or not config.COL_USER_TG_ID:
        return []
    try:
        rows = await client.list_objects(config.APIARY_T_USERS, page_size=200)
        result: list[int] = []
        for row in rows:
            # Если list_objects вернул requisites — читаем напрямую (без N+1)
            # Если нет — fallback на get_object
            is_active = _row_value(row, config.COL_USER_ACTIVE)
            tg_id_raw = _row_value(row, config.COL_USER_TG_ID)
            if not is_active or not tg_id_raw:
                # list_objects не включил requisites — получаем полный объект
                if config.COL_USER_ACTIVE:
                    full = await client.get_object(row["id"])
                    if full is None:
                        continue
                    reqs = full.get("requisites", {})
                    is_active = reqs.get(str(config.COL_USER_ACTIVE))
                    if not is_active:
                        continue
                    tg_id_raw = reqs.get(str(config.COL_USER_TG_ID))
                else:
                    tg_id_raw = _row_value(row, config.COL_USER_TG_ID)
            if not is_active:
                continue
            if tg_id_raw:
                try:
                    result.append(int(tg_id_raw))
                except (ValueError, TypeError):
                    logger.warning("get_active_user_tg_ids: невалидный tg_id=%r", tg_id_raw)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_active_user_tg_ids: ошибка запроса: %s", exc)
        return []
