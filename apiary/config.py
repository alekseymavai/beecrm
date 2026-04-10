"""apiary/config.py — конфигурация модуля BEEBOTLITE."""

import os

BOT_TOKEN: str = os.environ["BEEBOTLITE_TOKEN"]
GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
ADMIN_TG_ID: int = int(os.environ["BEEBOTLITE_ADMIN_TG_ID"])

# Учётные данные Integram (берутся из общих настроек)
INTEGRAM_LOGIN: str = os.environ["INTEGRAM_LOGIN"]
INTEGRAM_PASSWORD: str = os.environ["INTEGRAM_PASSWORD"]
INTEGRAM_WORKSPACE: str = os.environ.get("INTEGRAM_WORKSPACE", "beecrm")

# ── typeId таблиц пасеки (заполнить после create_tables.py) ──────────────────
# Задаются через env или вписываются после запуска скрипта инициализации.
# Пример: APIARY_T_ROLES=101 APIARY_T_HEALTH=102 ...
APIARY_T_ROLES: int = int(os.environ.get("APIARY_T_ROLES", "0"))
APIARY_T_HEALTH: int = int(os.environ.get("APIARY_T_HEALTH", "0"))
APIARY_T_HIVES: int = int(os.environ.get("APIARY_T_HIVES", "0"))
APIARY_T_USERS: int = int(os.environ.get("APIARY_T_USERS", "0"))
APIARY_T_INSPECTIONS: int = int(os.environ.get("APIARY_T_INSPECTIONS", "0"))

# ── колонки таблиц (заполнить после create_tables.py) ────────────────────────
# Ульи
COL_HIVE_LOCATION: int = int(os.environ.get("APIARY_COL_HIVE_LOCATION", "0"))
COL_HIVE_NOTES: int = int(os.environ.get("APIARY_COL_HIVE_NOTES", "0"))
COL_HIVE_ACTIVE: int = int(os.environ.get("APIARY_COL_HIVE_ACTIVE", "0"))

# Пользователи бота
COL_USER_TG_ID: int = int(os.environ.get("APIARY_COL_USER_TG_ID", "0"))
COL_USER_USERNAME: int = int(os.environ.get("APIARY_COL_USER_USERNAME", "0"))
COL_USER_ROLE: int = int(os.environ.get("APIARY_COL_USER_ROLE", "0"))
COL_USER_ACTIVE: int = int(os.environ.get("APIARY_COL_USER_ACTIVE", "0"))

# Осмотры
COL_INSP_HIVE_ID: int = int(os.environ.get("APIARY_COL_INSP_HIVE_ID", "0"))
COL_INSP_DATE: int = int(os.environ.get("APIARY_COL_INSP_DATE", "0"))
COL_INSP_INSPECTOR_TG_ID: int = int(os.environ.get("APIARY_COL_INSP_INSPECTOR_TG_ID", "0"))
COL_INSP_QUEEN_SEEN: int = int(os.environ.get("APIARY_COL_INSP_QUEEN_SEEN", "0"))
COL_INSP_BROOD_STATUS: int = int(os.environ.get("APIARY_COL_INSP_BROOD_STATUS", "0"))
COL_INSP_HONEY_AMOUNT: int = int(os.environ.get("APIARY_COL_INSP_HONEY_AMOUNT", "0"))
COL_INSP_HEALTH_STATUS: int = int(os.environ.get("APIARY_COL_INSP_HEALTH_STATUS", "0"))
COL_INSP_ACTIONS_TAKEN: int = int(os.environ.get("APIARY_COL_INSP_ACTIONS_TAKEN", "0"))
COL_INSP_NOTES: int = int(os.environ.get("APIARY_COL_INSP_NOTES", "0"))
COL_INSP_NEEDS_ATTENTION: int = int(os.environ.get("APIARY_COL_INSP_NEEDS_ATTENTION", "0"))
COL_INSP_IS_DRAFT: int = int(os.environ.get("APIARY_COL_INSP_IS_DRAFT", "0"))
COL_INSP_SESSION_ID: int = int(os.environ.get("APIARY_COL_INSP_SESSION_ID", "0"))
COL_INSP_RAW_TEXT: int = int(os.environ.get("APIARY_COL_INSP_RAW_TEXT", "0"))
