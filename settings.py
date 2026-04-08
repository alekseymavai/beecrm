import os

# Единственный источник лимита payload — импортируется в схемы и адаптеры
MAX_PAYLOAD_BYTES: int = 65536

REQUIRED_VARS = ("SECRET_KEY", "API_KEY", "INTEGRAM_LOGIN", "INTEGRAM_PASSWORD")

SECRET_KEY: str = ""
API_KEY: str = ""
INTEGRAM_LOGIN: str = ""
INTEGRAM_PASSWORD: str = ""
INTEGRAM_T_EVENTS: int = 0   # ID child-таблицы OrderEvent; 0 = отключено


def startup_check() -> None:
    """Вызывать при старте приложения. ValueError если обязательная переменная не задана."""
    missing = [key for key in REQUIRED_VARS if key not in os.environ]
    if missing:
        raise ValueError(f"Обязательные переменные не заданы: {', '.join(missing)}")

    global SECRET_KEY, API_KEY, INTEGRAM_LOGIN, INTEGRAM_PASSWORD, INTEGRAM_T_EVENTS
    SECRET_KEY = os.environ["SECRET_KEY"]
    API_KEY = os.environ["API_KEY"]
    INTEGRAM_LOGIN = os.environ["INTEGRAM_LOGIN"]
    INTEGRAM_PASSWORD = os.environ["INTEGRAM_PASSWORD"]
    INTEGRAM_T_EVENTS = int(os.environ.get("INTEGRAM_T_EVENTS", "0"))
