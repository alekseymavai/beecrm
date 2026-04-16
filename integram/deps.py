import hmac

from fastapi import Header, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt

import settings
from integram.client import IntegramClient

_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_integram(request: Request) -> IntegramClient:
    return request.app.state.integram


async def get_current_user(
    authorization: str | None = Header(None),
    api_key: str | None = Security(_header_scheme),
) -> dict:
    """Получить текущего пользователя из JWT или X-API-Key.

    Returns:
        dict: {"username": str, "role": str}

    Raises:
        HTTPException(401): Если нет валидной аутентификации
    """
    # 1. JWT (приоритет выше)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
            return {
                "username": payload["sub"],
                "role": payload.get("role", "Менеджер"),
            }
        except JWTError:
            pass  # Продолжить на X-API-Key fallback

    # 2. X-API-Key (fallback)
    if api_key and hmac.compare_digest(api_key, settings.API_KEY):
        return {"username": "api", "role": "API"}

    raise HTTPException(status_code=401, detail="Требуется аутентификация")
