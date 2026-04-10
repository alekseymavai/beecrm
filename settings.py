import logging
import os

logger = logging.getLogger(__name__)

# Единственный источник лимита payload — импортируется в схемы и адаптеры
MAX_PAYLOAD_BYTES: int = 65536

REQUIRED_VARS = ("API_KEY", "INTEGRAM_LOGIN", "INTEGRAM_PASSWORD")

API_KEY: str = ""
INTEGRAM_LOGIN: str = ""
INTEGRAM_PASSWORD: str = ""
INTEGRAM_WORKSPACE: str = "beecrm"
INTEGRAM_T_EVENTS: int = 37   # ID child-таблицы OrderEvent (typeId 37); 0 = отключено
CORS_ORIGINS: list[str] = []


def startup_check() -> None:
    """Вызывать при старте приложения. ValueError если обязательная переменная не задана."""
    missing = [key for key in REQUIRED_VARS if key not in os.environ]
    if missing:
        raise ValueError(f"Обязательные переменные не заданы: {', '.join(missing)}")

    global API_KEY, INTEGRAM_LOGIN, INTEGRAM_PASSWORD, INTEGRAM_WORKSPACE, INTEGRAM_T_EVENTS, CORS_ORIGINS
    API_KEY = os.environ["API_KEY"]
    INTEGRAM_LOGIN = os.environ["INTEGRAM_LOGIN"]
    INTEGRAM_PASSWORD = os.environ["INTEGRAM_PASSWORD"]
    INTEGRAM_WORKSPACE = os.environ.get("INTEGRAM_WORKSPACE", "beecrm")
    INTEGRAM_T_EVENTS = int(os.environ.get("INTEGRAM_T_EVENTS", "37"))
    cors_raw = os.environ.get("CORS_ORIGINS", "")
    CORS_ORIGINS = [o.strip() for o in cors_raw.split(",") if o.strip()]

    if INTEGRAM_T_EVENTS == 0:
        logger.warning("INTEGRAM_T_EVENTS=0 — история заказов отключена. Задайте INTEGRAM_T_EVENTS в .env.")
    if not CORS_ORIGINS:
        logger.warning("CORS_ORIGINS не задан — CORS отключён для браузеров. Задайте CORS_ORIGINS в .env.")


# ── BEEBOTLITE ────────────────────────────────────────────────────────────────
# Переменные модуля apiary/ читаются напрямую через os.environ в apiary/config.py.
# Здесь объявлены только для документирования и возможного использования в main.
BEEBOTLITE_TOKEN: str = os.environ.get("BEEBOTLITE_TOKEN", "")
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
BEEBOTLITE_ADMIN_TG_ID: str = os.environ.get("BEEBOTLITE_ADMIN_TG_ID", "")

# ── UDS ───────────────────────────────────────────────────────────────────────
# Переменные модуля uds/ читаются напрямую через os.environ в uds/config.py.
# UDS_ADMIN_TOKEN, UDS_COMPANY_ID, UDS_POLL_INTERVAL, UDS_INITIAL_SYNC
