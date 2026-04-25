"""apiary/scripts/create_tables.py — одноразовый скрипт создания таблиц пасеки в Integram.

Запуск (из корня BEECRM):
    python -m apiary.scripts.create_tables

После выполнения скрипт выведет typeId и colId всех созданных таблиц.
Скопируйте их в .env и перезапустите бота.

ВАЖНО: Integram API должен быть доступен (check: GET https://ai2o.online/api/v2/iam/login).
"""

from __future__ import annotations

import asyncio
import os
import sys


async def main() -> None:
    login = os.environ.get("INTEGRAM_LOGIN")
    password = os.environ.get("INTEGRAM_PASSWORD")
    workspace = os.environ.get("INTEGRAM_WORKSPACE", "usadba")

    if not login or not password:
        print("ERROR: INTEGRAM_LOGIN и INTEGRAM_PASSWORD должны быть заданы в .env")
        sys.exit(1)

    # Импортируем после проверки env
    from integram.client import IntegramClient
    from integram.exceptions import IntegramError

    print(f"Подключаемся к Integram workspace '{workspace}'...")
    client = await IntegramClient.authenticate(login, password, workspace=workspace)

    results: dict[str, dict] = {}

    # ── 1. Роли пасеки ────────────────────────────────────────────────────────
    print("\n[1/5] Создаём таблицу 'Роли пасеки'...")
    try:
        # Используем search_tools=schema для создания таблицы через MCP,
        # но здесь делаем через прямой API Integram.
        # Создаём объект-тип (справочник) через POST /types
        resp = await client._request(
            "POST", f"{client.BASE}/types",
            json={"name": "Роли пасеки", "isRef": True}
        )
        roles_type_id = resp.get("id") or resp.get("typeId")
        print(f"  typeId: {roles_type_id}")
        results["APIARY_T_ROLES"] = {"typeId": roles_type_id, "cols": {}}

        # Записи справочника
        for role_name in ["Пчеловод", "Старший пчеловод", "Администратор"]:
            obj = await client.create_object(roles_type_id, value=role_name)
            print(f"  Создана роль '{role_name}' (id={obj['id']})")

    except Exception as exc:
        print(f"  ОШИБКА: {exc}")
        print("  Проверьте доступность Integram API и повторите.")
        await client.close()
        sys.exit(1)

    # ── 2. Статусы здоровья ───────────────────────────────────────────────────
    print("\n[2/5] Создаём таблицу 'Статусы здоровья'...")
    try:
        resp = await client._request(
            "POST", f"{client.BASE}/types",
            json={"name": "Статусы здоровья", "isRef": True}
        )
        health_type_id = resp.get("id") or resp.get("typeId")
        print(f"  typeId: {health_type_id}")
        results["APIARY_T_HEALTH"] = {"typeId": health_type_id, "cols": {}}

        for status_name in ["Здоров", "Требует внимания", "Болен", "Подозрение"]:
            obj = await client.create_object(health_type_id, value=status_name)
            print(f"  Создан статус '{status_name}' (id={obj['id']})")

    except Exception as exc:
        print(f"  ОШИБКА: {exc}")
        await client.close()
        sys.exit(1)

    # ── 3. Ульи ───────────────────────────────────────────────────────────────
    print("\n[3/5] Создаём таблицу 'Ульи'...")
    try:
        resp = await client._request(
            "POST", f"{client.BASE}/types",
            json={"name": "Ульи"}
        )
        hives_type_id = resp.get("id") or resp.get("typeId")
        print(f"  typeId: {hives_type_id}")
        results["APIARY_T_HIVES"] = {"typeId": hives_type_id, "cols": {}}

        hive_cols = [
            {"alias": "location", "name": "Расположение", "colTypeName": "string"},
            {"alias": "notes", "name": "Заметки", "colTypeName": "memo"},
            {"alias": "is_active", "name": "Активен", "colTypeName": "bool"},
        ]
        for col in hive_cols:
            c = await client._request(
                "POST", f"{client.BASE}/types/{hives_type_id}/requisites",
                json=col
            )
            col_id = c.get("id") or c.get("reqId")
            results["APIARY_T_HIVES"]["cols"][col["alias"]] = col_id
            print(f"  Колонка '{col['name']}' (id={col_id})")

    except Exception as exc:
        print(f"  ОШИБКА: {exc}")
        await client.close()
        sys.exit(1)

    # ── 4. Пользователи бота ──────────────────────────────────────────────────
    print("\n[4/5] Создаём таблицу 'Пользователи бота'...")
    try:
        resp = await client._request(
            "POST", f"{client.BASE}/types",
            json={"name": "Пользователи бота"}
        )
        users_type_id = resp.get("id") or resp.get("typeId")
        print(f"  typeId: {users_type_id}")
        results["APIARY_T_USERS"] = {"typeId": users_type_id, "cols": {}}

        users_cols = [
            {"alias": "tg_id", "name": "Telegram ID", "colTypeName": "string"},
            {"alias": "tg_username", "name": "Username", "colTypeName": "string"},
            {"alias": "role", "name": "Роль", "colTypeName": "ref", "refTypeId": roles_type_id},
            {"alias": "is_active", "name": "Активен", "colTypeName": "bool"},
        ]
        for col in users_cols:
            c = await client._request(
                "POST", f"{client.BASE}/types/{users_type_id}/requisites",
                json=col
            )
            col_id = c.get("id") or c.get("reqId")
            results["APIARY_T_USERS"]["cols"][col["alias"]] = col_id
            print(f"  Колонка '{col['name']}' (id={col_id})")

    except Exception as exc:
        print(f"  ОШИБКА: {exc}")
        await client.close()
        sys.exit(1)

    # ── 5. Осмотры ────────────────────────────────────────────────────────────
    print("\n[5/5] Создаём таблицу 'Осмотры'...")
    try:
        resp = await client._request(
            "POST", f"{client.BASE}/types",
            json={"name": "Осмотры"}
        )
        insp_type_id = resp.get("id") or resp.get("typeId")
        print(f"  typeId: {insp_type_id}")
        results["APIARY_T_INSPECTIONS"] = {"typeId": insp_type_id, "cols": {}}

        insp_cols = [
            {"alias": "hive_id", "name": "Улей", "colTypeName": "ref", "refTypeId": hives_type_id},
            {"alias": "inspection_date", "name": "Дата осмотра", "colTypeName": "date"},
            {"alias": "inspector_tg_id", "name": "Инспектор TG ID", "colTypeName": "string"},
            {"alias": "queen_seen", "name": "Матка видна", "colTypeName": "bool"},
            {"alias": "brood_status", "name": "Расплод", "colTypeName": "memo"},
            {"alias": "honey_amount", "name": "Количество мёда", "colTypeName": "string"},
            {"alias": "health_status", "name": "Статус здоровья", "colTypeName": "ref", "refTypeId": health_type_id},
            {"alias": "actions_taken", "name": "Действия", "colTypeName": "memo"},
            {"alias": "notes", "name": "Заметки", "colTypeName": "memo"},
            {"alias": "needs_attention", "name": "Требует внимания", "colTypeName": "bool"},
            {"alias": "is_draft", "name": "Черновик", "colTypeName": "bool"},
            {"alias": "session_id", "name": "ID сессии", "colTypeName": "string"},
            {"alias": "raw_text", "name": "Исходный текст", "colTypeName": "memo"},
        ]
        for col in insp_cols:
            c = await client._request(
                "POST", f"{client.BASE}/types/{insp_type_id}/requisites",
                json=col
            )
            col_id = c.get("id") or c.get("reqId")
            results["APIARY_T_INSPECTIONS"]["cols"][col["alias"]] = col_id
            print(f"  Колонка '{col['name']}' (id={col_id})")

    except Exception as exc:
        print(f"  ОШИБКА: {exc}")
        await client.close()
        sys.exit(1)

    await client.close()

    # ── Итоговый вывод для .env ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("ГОТОВО! Скопируйте в .env:\n")
    print(f"APIARY_T_ROLES={results['APIARY_T_ROLES']['typeId']}")
    print(f"APIARY_T_HEALTH={results['APIARY_T_HEALTH']['typeId']}")

    hc = results["APIARY_T_HIVES"]["cols"]
    print(f"APIARY_T_HIVES={results['APIARY_T_HIVES']['typeId']}")
    print(f"APIARY_COL_HIVE_LOCATION={hc.get('location', '')}")
    print(f"APIARY_COL_HIVE_NOTES={hc.get('notes', '')}")
    print(f"APIARY_COL_HIVE_ACTIVE={hc.get('is_active', '')}")

    uc = results["APIARY_T_USERS"]["cols"]
    print(f"APIARY_T_USERS={results['APIARY_T_USERS']['typeId']}")
    print(f"APIARY_COL_USER_TG_ID={uc.get('tg_id', '')}")
    print(f"APIARY_COL_USER_USERNAME={uc.get('tg_username', '')}")
    print(f"APIARY_COL_USER_ROLE={uc.get('role', '')}")
    print(f"APIARY_COL_USER_ACTIVE={uc.get('is_active', '')}")

    ic = results["APIARY_T_INSPECTIONS"]["cols"]
    print(f"APIARY_T_INSPECTIONS={results['APIARY_T_INSPECTIONS']['typeId']}")
    print(f"APIARY_COL_INSP_HIVE_ID={ic.get('hive_id', '')}")
    print(f"APIARY_COL_INSP_DATE={ic.get('inspection_date', '')}")
    print(f"APIARY_COL_INSP_INSPECTOR_TG_ID={ic.get('inspector_tg_id', '')}")
    print(f"APIARY_COL_INSP_QUEEN_SEEN={ic.get('queen_seen', '')}")
    print(f"APIARY_COL_INSP_BROOD_STATUS={ic.get('brood_status', '')}")
    print(f"APIARY_COL_INSP_HONEY_AMOUNT={ic.get('honey_amount', '')}")
    print(f"APIARY_COL_INSP_HEALTH_STATUS={ic.get('health_status', '')}")
    print(f"APIARY_COL_INSP_ACTIONS_TAKEN={ic.get('actions_taken', '')}")
    print(f"APIARY_COL_INSP_NOTES={ic.get('notes', '')}")
    print(f"APIARY_COL_INSP_NEEDS_ATTENTION={ic.get('needs_attention', '')}")
    print(f"APIARY_COL_INSP_IS_DRAFT={ic.get('is_draft', '')}")
    print(f"APIARY_COL_INSP_SESSION_ID={ic.get('session_id', '')}")
    print(f"APIARY_COL_INSP_RAW_TEXT={ic.get('raw_text', '')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
