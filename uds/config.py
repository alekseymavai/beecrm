"""uds/config.py — переменные окружения UDS модуля.

Читает env напрямую (не через settings.py) — модуль опциональный.
"""

import logging
import os

logger = logging.getLogger(__name__)

UDS_ADMIN_TOKEN: str = os.environ.get("UDS_ADMIN_TOKEN", "")
UDS_COMPANY_ID: str = os.environ.get("UDS_COMPANY_ID", "")
UDS_POLL_INTERVAL: int = int(os.environ.get("UDS_POLL_INTERVAL", "60"))
UDS_INITIAL_SYNC: bool = os.environ.get("UDS_INITIAL_SYNC", "false").lower() == "true"


def check() -> None:
    """Проверить конфиг. WARNING если TOKEN не задан — не raises (модуль опциональный)."""
    if not UDS_ADMIN_TOKEN:
        logger.warning(
            "UDS_ADMIN_TOKEN не задан — UDS polling отключён. "
            "Задайте UDS_ADMIN_TOKEN в .env для активации интеграции."
        )
    if not UDS_COMPANY_ID:
        logger.warning(
            "UDS_COMPANY_ID не задан — UDS polling отключён. "
            "Задайте UDS_COMPANY_ID в .env."
        )
    if UDS_INITIAL_SYNC:
        logger.warning(
            "UDS_INITIAL_SYNC=true задан, но начальная синхронизация не реализована. "
            "Будет выполнен только текущий polling."
        )
