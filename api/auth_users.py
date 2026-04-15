"""api/auth_users.py — JWT-аутентификация: login и register."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel, Field

import settings
from integram.client import IntegramClient
from integram.deps import get_integram

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


class LoginRequest(BaseModel):
    login: str = Field(min_length=1)
    password: str = Field(min_length=3)


class RegisterRequest(BaseModel):
    login: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=3, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


def _make_token(username: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "role": role, "exp": exp},
        settings.JWT_SECRET,
        algorithm="HS256",
    )


async def _find_user(igm: IntegramClient, login: str) -> dict | None:
    return await igm.find_by_field(igm.T_USERS, igm.COL_USER_LOGIN, login)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    igm: IntegramClient = Depends(get_integram),
) -> TokenResponse:
    user = await _find_user(igm, body.login)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    req = user.get("requisites") or {}
    hashed = req.get(str(igm.COL_USER_HASH), "")
    if not _verify_password(body.password, hashed):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    is_active = req.get(str(igm.COL_USER_ACTIVE), True)
    if not is_active:
        raise HTTPException(status_code=403, detail="Аккаунт деактивирован")

    role_id = req.get(str(igm.COL_USER_ROLE))
    role_name = igm.ROLE_NAMES.get(int(role_id), "Менеджер") if role_id else "Менеджер"

    return TokenResponse(
        access_token=_make_token(body.login, role_name),
        username=body.login,
        role=role_name,
    )


@router.post("/register", response_model=TokenResponse, status_code=200)
async def register(
    body: RegisterRequest,
    igm: IntegramClient = Depends(get_integram),
) -> TokenResponse:
    existing = await _find_user(igm, body.login)
    if existing:
        raise HTTPException(status_code=409, detail="Логин уже занят")

    hashed = _hash_password(body.password)
    await igm.create_object(
        typeId=igm.T_USERS,
        value=body.login,
        requisites={
            str(igm.COL_USER_LOGIN): body.login,
            str(igm.COL_USER_HASH): hashed,
            str(igm.COL_USER_ROLE): igm.ROLE_MANAGER_ID,
            str(igm.COL_USER_ACTIVE): True,
        },
    )

    return TokenResponse(
        access_token=_make_token(body.login, "Менеджер"),
        username=body.login,
        role="Менеджер",
    )
