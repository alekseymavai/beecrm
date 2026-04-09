"""auth.py — API Key аутентификация.

Все роутеры подключают этот dependency через main.py.
Ключ передаётся в заголовке X-API-Key.
Возвращаем 403 (не 401) — не раскрываем схему аутентификации.
"""

import hmac

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

import settings

_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(_header_scheme)) -> None:
    if not api_key or not hmac.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(status_code=403, detail="Доступ запрещён")
