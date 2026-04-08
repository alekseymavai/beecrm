import os

# Единственный источник лимита payload — импортируется в схемы и миграцию
MAX_PAYLOAD_BYTES: int = 65536

REQUIRED_VARS = ("DB_URL", "SECRET_KEY", "API_KEY")

# Секреты — только os.environ[KEY], никаких .get(KEY, default)
DB_URL: str = os.environ.get("DB_URL", "")        # заполняется после startup_check()
SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
API_KEY: str = os.environ.get("API_KEY", "")


def startup_check() -> None:
    """Вызывать при старте приложения. KeyError если обязательная переменная не задана."""
    missing = [key for key in REQUIRED_VARS if key not in os.environ]
    if missing:
        raise ValueError(f"Обязательные переменные не заданы: {', '.join(missing)}")

    global DB_URL, SECRET_KEY, API_KEY
    DB_URL = os.environ["DB_URL"]
    SECRET_KEY = os.environ["SECRET_KEY"]
    API_KEY = os.environ["API_KEY"]
