"""auth.py — Аутентификация: X-API-Key (обратная совместимость) или Bearer JWT.

Порядок проверки:
1. X-API-Key — если совпадает с settings.API_KEY, доступ разрешён.
2. Authorization: Bearer <token> — если JWT валидный, доступ разрешён.
3. Иначе — 403.
"""
import hmac

from fastapi import Header, HTTPException, Security
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt

import settings

_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(
    api_key: str | None = Security(_header_scheme),
    authorization: str | None = Header(default=None),
) -> None:
    # 1. X-API-Key
    if api_key and hmac.compare_digest(api_key, settings.API_KEY):
        return
    # 2. Bearer JWT
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            return
        except JWTError:
            pass
    raise HTTPException(status_code=403, detail="Доступ запрещён")
