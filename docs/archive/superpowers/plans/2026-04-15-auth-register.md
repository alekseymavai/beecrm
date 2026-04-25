# Auth + Register Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить JWT-аутентификацию с логином/паролем и регистрацией в Vue-дашборд BEECRM — хранение пользователей в Integram workspace `beecrm`.

**Architecture:** Бэкенд получает два новых эндпоинта (`POST /auth/login`, `POST /auth/register`) — пользователи хранятся в таблице Integram «Пользователи CRM», роли — в lookup-таблице «Роли пользователей». Существующая `verify_api_key` расширяется: принимает либо `X-API-Key` (обратная совместимость), либо `Authorization: Bearer <jwt>` (для дашборда). Фронтенд переключается с хранения API-ключа на JWT в `localStorage`.

**Tech Stack:** FastAPI + python-jose (JWT HS256) + passlib (bcrypt), Vue 3 + Pinia, Integram API (IntegramClient), PrimeVue 4, Tailwind 4.

---

## Карта файлов

| Статус | Путь | Ответственность |
|--------|------|-----------------|
| NEW | `api/auth_users.py` | POST /auth/login, POST /auth/register, get_current_user dependency |
| NEW | `dashboard/src/views/RegisterView.vue` | форма регистрации |
| NEW | `tests/test_auth_users.py` | тесты JWT-эндпоинтов |
| MOD | `requirements.txt` | + python-jose, passlib |
| MOD | `settings.py` | + JWT_SECRET, JWT_EXPIRE_MINUTES |
| MOD | `api/auth.py` | verify_api_key принимает Bearer JWT |
| MOD | `main.py` | include auth_users router |
| MOD | `integram/client.py` | + T_USERS, T_USER_ROLES, role/col IDs |
| MOD | `tests/mocks/integram_mock.py` | + те же константы |
| MOD | `dashboard/src/stores/auth.js` | JWT-based: login/register/logout/decoded user |
| MOD | `dashboard/src/api/http.js` | Authorization: Bearer вместо X-API-Key |
| MOD | `dashboard/src/views/LoginView.vue` | поля login + password вместо API-ключа |
| MOD | `dashboard/src/router/index.js` | + /register маршрут, guard по JWT |
| MOD | `dashboard/src/layout/AppSidebar.vue` | реальный username из store |
| MOD | `dashboard/src/layout/AppTopbar.vue` | реальная первая буква username |

---

## Task 0: Integram — создать таблицы пользователей (MCP)

**Инструмент:** MCP integram (beecrm workspace). Нужен ручной запуск через MCP-клиент или Claude.

- [ ] **Step 1: Переключиться в workspace beecrm**

```
mcp__integram__switch_workspace(slug="beecrm")
```

- [ ] **Step 2: Активировать schema-инструменты**

```
mcp__integram__search_tools(query="schema")
```

- [ ] **Step 3: Создать lookup-таблицу ролей**

```
mcp__integram__create_table(name="Роли пользователей")
```

Записать полученный `id` → далее называем `T_USER_ROLES`.

- [ ] **Step 4: Создать записи ролей**

```
mcp__integram__create_object(typeId=T_USER_ROLES, value="Администратор")
mcp__integram__create_object(typeId=T_USER_ROLES, value="Менеджер")
```

Записать ID первой записи → `ROLE_ADMIN_ID`, второй → `ROLE_MANAGER_ID`.

- [ ] **Step 5: Создать таблицу пользователей**

```
mcp__integram__create_table(name="Пользователи CRM")
```

Записать `id` → `T_USERS`.

- [ ] **Step 6: Добавить колонки**

```
# login — уникальный логин
mcp__integram__add_column(typeId=T_USERS, alias="login", colTypeName="string")
→ записать id → COL_USER_LOGIN

# password_hash — bcrypt-хеш
mcp__integram__add_column(typeId=T_USERS, alias="password_hash", colTypeName="string")
→ записать id → COL_USER_HASH

# role — ref на Роли пользователей
mcp__integram__add_column(typeId=T_USERS, alias="role", colTypeName="ref", refTypeId=T_USER_ROLES)
→ записать id → COL_USER_ROLE

# is_active — флаг активности
mcp__integram__add_column(typeId=T_USERS, alias="is_active", colTypeName="bool")
→ записать id → COL_USER_ACTIVE
```

- [ ] **Step 7: Записать все ID в таблицу для следующих задач**

```
T_USER_ROLES = ___
T_USERS      = ___
ROLE_ADMIN_ID  = ___
ROLE_MANAGER_ID = ___
COL_USER_LOGIN  = ___
COL_USER_HASH   = ___
COL_USER_ROLE   = ___
COL_USER_ACTIVE = ___
```

> **СТОП**: передай ID в следующие задачи перед продолжением.

---

## Task 1: Backend — зависимости и настройки

**Files:**
- Modify: `requirements.txt`
- Modify: `settings.py`

- [ ] **Step 1: Добавить зависимости**

`requirements.txt` — добавить после строки `python-multipart`:
```
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

- [ ] **Step 2: Добавить JWT-настройки в settings.py**

В `REQUIRED_VARS` добавить `"JWT_SECRET"`:
```python
REQUIRED_VARS = ("API_KEY", "INTEGRAM_LOGIN", "INTEGRAM_PASSWORD", "JWT_SECRET")
```

После блока `CORS_ORIGINS: list[str] = []` добавить:
```python
JWT_SECRET: str = ""
JWT_EXPIRE_MINUTES: int = 1440  # 24 часа
```

В функции `startup_check()`, после `CORS_ORIGINS = ...`:
```python
global JWT_SECRET, JWT_EXPIRE_MINUTES
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))
```

- [ ] **Step 3: Установить зависимости**

```bash
pip install "python-jose[cryptography]>=3.3.0" "passlib[bcrypt]>=1.7.4"
```

Ожидаемый вывод: `Successfully installed python-jose-... passlib-...`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt settings.py
git commit -m "feat(auth): add JWT deps + JWT_SECRET setting"
```

---

## Task 2: IntegramClient — константы пользователей

> Подставить ID из Task 0 вместо заглушек `999`.

**Files:**
- Modify: `integram/client.py` (класс IntegramClient, блок констант)
- Modify: `tests/mocks/integram_mock.py` (класс FakeIntegramClient)

- [ ] **Step 1: Добавить константы в IntegramClient**

В `integram/client.py`, в тело класса `IntegramClient`, после строки с `T_PRODUCTS = 52`:
```python
# ── Users ─────────────────────────────────────────────────────────────────
T_USER_ROLES = ___   # «Роли пользователей» — из Task 0
T_USERS      = ___   # «Пользователи CRM»   — из Task 0
ROLE_ADMIN_ID   = ___  # запись «Администратор» — из Task 0
ROLE_MANAGER_ID = ___  # запись «Менеджер»      — из Task 0
ROLE_NAMES: dict[int, str] = {}  # заполняется ниже

COL_USER_LOGIN  = ___  # из Task 0
COL_USER_HASH   = ___  # из Task 0
COL_USER_ROLE   = ___  # из Task 0
COL_USER_ACTIVE = ___  # из Task 0
```

После блока констант класса (внутри `__init__` или как class-level code) добавить:
```python
IntegramClient.ROLE_NAMES = {
    IntegramClient.ROLE_ADMIN_ID:   "Администратор",
    IntegramClient.ROLE_MANAGER_ID: "Менеджер",
}
```

Это можно разместить сразу после объявления класса (вне тела, но в том же файле).

- [ ] **Step 2: Добавить те же константы в FakeIntegramClient**

В `tests/mocks/integram_mock.py`, после `T_PRODUCTS = 52`:
```python
T_USER_ROLES    = 200   # фиктивный ID для тестов
T_USERS         = 201
ROLE_ADMIN_ID   = 500
ROLE_MANAGER_ID = 501
ROLE_NAMES      = {500: "Администратор", 501: "Менеджер"}

COL_USER_LOGIN  = 202
COL_USER_HASH   = 203
COL_USER_ROLE   = 204
COL_USER_ACTIVE = 205
```

- [ ] **Step 3: Убедиться что тесты всё ещё зелёные**

```bash
pytest tests/ -q
```

Ожидаемый вывод: все тесты PASSED (ничего не сломали).

- [ ] **Step 4: Commit**

```bash
git add integram/client.py tests/mocks/integram_mock.py
git commit -m "feat(auth): add user table constants to IntegramClient"
```

---

## Task 3: api/auth_users.py — JWT-эндпоинты (TDD)

**Files:**
- Create: `tests/test_auth_users.py`
- Create: `api/auth_users.py`

- [ ] **Step 1: Написать тесты**

Создать `tests/test_auth_users.py`:
```python
"""test_auth_users.py — тесты JWT login/register."""
import os
import pytest
from passlib.context import CryptContext

os.environ.setdefault("JWT_SECRET", "test-secret-key-32-chars-minimum!!")

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestRegister:
    def test_register_creates_user_and_returns_token(self, client, igm):
        resp = client.post("/auth/register", json={"login": "alice", "password": "pass123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == "alice"
        assert data["token_type"] == "bearer"

    def test_register_duplicate_login_returns_409(self, client, igm):
        client.post("/auth/register", json={"login": "bob", "password": "pass"})
        resp = client.post("/auth/register", json={"login": "bob", "password": "pass"})
        assert resp.status_code == 409

    def test_register_short_password_returns_422(self, client):
        resp = client.post("/auth/register", json={"login": "carol", "password": "ab"})
        assert resp.status_code == 422

    def test_register_empty_login_returns_422(self, client):
        resp = client.post("/auth/register", json={"login": "", "password": "pass123"})
        assert resp.status_code == 422


class TestLogin:
    def _seed_user(self, igm, login="dave", password="secret"):
        """Создать пользователя в FakeIntegramClient."""
        hashed = _pwd.hash(password)
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            igm.create_object(
                typeId=igm.T_USERS,
                value=login,
                requisites={
                    str(igm.COL_USER_LOGIN): login,
                    str(igm.COL_USER_HASH): hashed,
                    str(igm.COL_USER_ROLE): igm.ROLE_MANAGER_ID,
                    str(igm.COL_USER_ACTIVE): True,
                },
            )
        )

    def test_login_returns_token(self, client, igm):
        self._seed_user(igm)
        resp = client.post("/auth/login", json={"login": "dave", "password": "secret"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["username"] == "dave"

    def test_login_wrong_password_returns_401(self, client, igm):
        self._seed_user(igm)
        resp = client.post("/auth/login", json={"login": "dave", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user_returns_401(self, client, igm):
        resp = client.post("/auth/login", json={"login": "ghost", "password": "pass"})
        assert resp.status_code == 401

    def test_login_inactive_user_returns_403(self, client, igm):
        hashed = _pwd.hash("pass")
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            igm.create_object(
                typeId=igm.T_USERS,
                value="inactive",
                requisites={
                    str(igm.COL_USER_LOGIN): "inactive",
                    str(igm.COL_USER_HASH): hashed,
                    str(igm.COL_USER_ROLE): igm.ROLE_MANAGER_ID,
                    str(igm.COL_USER_ACTIVE): False,
                },
            )
        )
        resp = client.post("/auth/login", json={"login": "inactive", "password": "pass"})
        assert resp.status_code == 403
```

- [ ] **Step 2: Запустить тесты — убедиться что падают**

```bash
pytest tests/test_auth_users.py -v
```

Ожидаемый вывод: `ImportError` или `404` — `auth_users` модуль ещё не создан.

- [ ] **Step 3: Создать api/auth_users.py**

```python
"""api/auth_users.py — JWT-аутентификация: login и register.

Хранение пользователей: Integram таблица T_USERS.
Токен: JWT HS256, payload: {"sub": username, "role": role_name, "exp": ...}.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

import settings
from integram.client import IntegramClient
from integram.deps import get_integram

router = APIRouter(prefix="/auth", tags=["auth"])
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Pydantic schemas ──────────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_token(username: str, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "role": role, "exp": exp},
        settings.JWT_SECRET,
        algorithm="HS256",
    )


async def _find_user(igm: IntegramClient, login: str) -> dict | None:
    return await igm.find_by_field(igm.T_USERS, igm.COL_USER_LOGIN, login)


# ── Endpoints ─────────────────────────────────────────────────────────────────

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
    if not _pwd.verify(body.password, hashed):
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

    hashed = _pwd.hash(body.password)
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
```

- [ ] **Step 4: Запустить тесты — убедиться что зелёные**

```bash
pytest tests/test_auth_users.py -v
```

Ожидаемый вывод: все 8 тестов PASSED.

- [ ] **Step 5: Commit**

```bash
git add api/auth_users.py tests/test_auth_users.py
git commit -m "feat(auth): JWT login/register endpoints + tests"
```

---

## Task 4: api/auth.py — поддержка Bearer JWT

**Files:**
- Modify: `api/auth.py`

Текущий `verify_api_key` принимает только `X-API-Key`. Расширяем: если заголовок `X-API-Key` отсутствует, пробуем `Authorization: Bearer <token>`.

- [ ] **Step 1: Написать тест на JWT-доступ**

В `tests/test_auth.py` добавить класс:
```python
class TestJwtAuth:
    def test_jwt_allows_access_to_clients(self, client):
        """Bearer JWT (с валидным JWT_SECRET) даёт доступ наравне с API Key."""
        import os
        from datetime import datetime, timedelta, timezone
        from jose import jwt as jose_jwt

        secret = os.environ.get("JWT_SECRET", "test-secret-key-32-chars-minimum!!")
        token = jose_jwt.encode(
            {"sub": "testuser", "role": "Администратор",
             "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            secret, algorithm="HS256",
        )
        resp = client.get("/clients/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code != 403

    def test_invalid_jwt_returns_403(self, client):
        resp = client.get("/clients/", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 403
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/test_auth.py::TestJwtAuth -v
```

Ожидаемый вывод: FAILED — `verify_api_key` не понимает Bearer.

- [ ] **Step 3: Обновить api/auth.py**

Полностью заменить содержимое файла:
```python
"""auth.py — Аутентификация: X-API-Key (обратная совместимость) или Bearer JWT.

Порядок проверки:
1. Заголовок X-API-Key — если совпадает с settings.API_KEY, доступ разрешён.
2. Заголовок Authorization: Bearer <token> — если JWT валидный, доступ разрешён.
3. Иначе — 403 (не 401, чтобы не раскрывать схему).
"""
import hmac

from fastapi import Depends, Header, HTTPException, Security
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
```

- [ ] **Step 4: Запустить все auth-тесты**

```bash
pytest tests/test_auth.py tests/test_auth_users.py -v
```

Ожидаемый вывод: все тесты PASSED.

- [ ] **Step 5: Запустить полный suite — ничего не сломали**

```bash
pytest tests/ -q
```

Ожидаемый вывод: все PASSED.

- [ ] **Step 6: Commit**

```bash
git add api/auth.py tests/test_auth.py
git commit -m "feat(auth): verify_api_key accepts Bearer JWT alongside X-API-Key"
```

---

## Task 5: main.py — подключить auth router

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Добавить import и регистрацию роутера**

После строки `from api.products import router as products_router` добавить:
```python
from api.auth_users import router as auth_users_router
```

После строки `app.include_router(uds_router)` добавить:
```python
app.include_router(auth_users_router)  # без _auth — это сам auth-эндпоинт
```

- [ ] **Step 2: Убедиться что сервер стартует**

```bash
cd /home/hive/BEECRM && JWT_SECRET=test-secret-32chars API_KEY=test INTEGRAM_LOGIN=x INTEGRAM_PASSWORD=x python -c "from main import app; print('OK')"
```

Ожидаемый вывод: `OK`

- [ ] **Step 3: Запустить все тесты**

```bash
pytest tests/ -q
```

Ожидаемый вывод: все PASSED.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(auth): register auth_users router in main.py"
```

---

## Task 6: Frontend — обновить auth store

**Files:**
- Modify: `dashboard/src/stores/auth.js`

- [ ] **Step 1: Заменить stores/auth.js**

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import http from '@/api/http.js';

const TOKEN_KEY = 'beecrm_jwt';

function decodeJwt(token) {
    try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(base64));
    } catch {
        return null;
    }
}

export const useAuthStore = defineStore('auth', () => {
    const token = ref(localStorage.getItem(TOKEN_KEY) || '');
    const loading = ref(false);
    const error = ref(null);

    const decoded = computed(() => (token.value ? decodeJwt(token.value) : null));
    const isLoggedIn = computed(() => {
        if (!decoded.value) return false;
        return decoded.value.exp * 1000 > Date.now();
    });
    const username = computed(() => decoded.value?.sub ?? '');
    const role = computed(() => decoded.value?.role ?? '');

    async function login(loginVal, password) {
        loading.value = true;
        error.value = null;
        try {
            const { data } = await http.post('/auth/login', { login: loginVal, password });
            token.value = data.access_token;
            localStorage.setItem(TOKEN_KEY, data.access_token);
        } catch (e) {
            const status = e.response?.status;
            if (status === 401) error.value = 'Неверный логин или пароль';
            else if (status === 403) error.value = 'Аккаунт деактивирован';
            else error.value = 'Ошибка сервера';
            throw e;
        } finally {
            loading.value = false;
        }
    }

    async function register(loginVal, password) {
        loading.value = true;
        error.value = null;
        try {
            const { data } = await http.post('/auth/register', { login: loginVal, password });
            token.value = data.access_token;
            localStorage.setItem(TOKEN_KEY, data.access_token);
        } catch (e) {
            const status = e.response?.status;
            if (status === 409) error.value = 'Логин уже занят';
            else if (status === 422) error.value = 'Слишком короткий пароль (мин. 3 символа)';
            else error.value = 'Ошибка регистрации';
            throw e;
        } finally {
            loading.value = false;
        }
    }

    function logout() {
        token.value = '';
        localStorage.removeItem(TOKEN_KEY);
    }

    return { token, isLoggedIn, username, role, loading, error, login, register, logout };
});
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/stores/auth.js
git commit -m "feat(auth): replace API-key store with JWT store (login/register/decoded user)"
```

---

## Task 7: Frontend — http client → Bearer token

**Files:**
- Modify: `dashboard/src/api/http.js`

- [ ] **Step 1: Заменить interceptor**

```javascript
import axios from 'axios';

const http = axios.create({
    baseURL: '/api',
    headers: { 'Cache-Control': 'no-store' },
});

http.interceptors.request.use((config) => {
    const token = localStorage.getItem('beecrm_jwt') || '';
    if (token) config.headers['Authorization'] = `Bearer ${token}`;
    return config;
});

export default http;
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/api/http.js
git commit -m "feat(auth): switch http client from X-API-Key to Bearer JWT"
```

---

## Task 8: Frontend — LoginView с логином и паролем

**Files:**
- Modify: `dashboard/src/views/LoginView.vue`

- [ ] **Step 1: Заменить LoginView.vue**

```vue
<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.js';

const router = useRouter();
const auth = useAuthStore();
const login = ref('');
const password = ref('');

async function submit() {
    if (!login.value.trim() || !password.value) return;
    try {
        await auth.login(login.value.trim(), password.value);
        router.push('/');
    } catch {}
}
</script>

<template>
    <div class="login-page">
        <div class="login-box">
            <div class="login-logo">BEECRM</div>
            <div class="login-title">Вход в систему</div>

            <div class="login-field">
                <label>Логин</label>
                <InputText
                    v-model="login"
                    placeholder="Введите логин"
                    class="w-full"
                    autocomplete="username"
                    @keyup.enter="submit"
                />
            </div>

            <div class="login-field" style="margin-top:12px">
                <label>Пароль</label>
                <InputText
                    v-model="password"
                    type="password"
                    placeholder="Введите пароль"
                    class="w-full"
                    autocomplete="current-password"
                    @keyup.enter="submit"
                />
            </div>

            <Message v-if="auth.error" severity="error" class="mt-2">{{ auth.error }}</Message>

            <Button
                label="Войти"
                :loading="auth.loading"
                class="w-full mt-3"
                @click="submit"
            />

            <div style="text-align:center; margin-top:16px">
                <button class="btn-link" @click="$router.push('/register')">
                    Нет аккаунта? Зарегистрироваться
                </button>
            </div>
        </div>
    </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/views/LoginView.vue
git commit -m "feat(auth): LoginView — login + password fields, link to register"
```

---

## Task 9: Frontend — RegisterView (новый компонент)

**Files:**
- Create: `dashboard/src/views/RegisterView.vue`

- [ ] **Step 1: Создать RegisterView.vue**

```vue
<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.js';

const router = useRouter();
const auth = useAuthStore();
const login = ref('');
const password = ref('');
const confirm = ref('');
const localError = ref('');

async function submit() {
    localError.value = '';
    if (!login.value.trim()) { localError.value = 'Введите логин'; return; }
    if (password.value.length < 3) { localError.value = 'Пароль — минимум 3 символа'; return; }
    if (password.value !== confirm.value) { localError.value = 'Пароли не совпадают'; return; }
    try {
        await auth.register(login.value.trim(), password.value);
        router.push('/');
    } catch {}
}

const errorMsg = () => localError.value || auth.error;
</script>

<template>
    <div class="login-page">
        <div class="login-box">
            <div class="login-logo">BEECRM</div>
            <div class="login-title">Регистрация</div>

            <div class="login-field">
                <label>Логин</label>
                <InputText
                    v-model="login"
                    placeholder="Придумайте логин"
                    class="w-full"
                    autocomplete="username"
                    @keyup.enter="submit"
                />
            </div>

            <div class="login-field" style="margin-top:12px">
                <label>Пароль</label>
                <InputText
                    v-model="password"
                    type="password"
                    placeholder="Минимум 3 символа"
                    class="w-full"
                    autocomplete="new-password"
                    @keyup.enter="submit"
                />
            </div>

            <div class="login-field" style="margin-top:12px">
                <label>Подтвердить пароль</label>
                <InputText
                    v-model="confirm"
                    type="password"
                    placeholder="Повторите пароль"
                    class="w-full"
                    autocomplete="new-password"
                    @keyup.enter="submit"
                />
            </div>

            <Message v-if="errorMsg()" severity="error" class="mt-2">{{ errorMsg() }}</Message>

            <Button
                label="Зарегистрироваться"
                :loading="auth.loading"
                class="w-full mt-3"
                @click="submit"
            />

            <div style="text-align:center; margin-top:16px">
                <button class="btn-link" @click="$router.push('/login')">
                    Уже есть аккаунт? Войти
                </button>
            </div>
        </div>
    </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/views/RegisterView.vue
git commit -m "feat(auth): add RegisterView component"
```

---

## Task 10: Frontend — router + navigation guard

**Files:**
- Modify: `dashboard/src/router/index.js`

- [ ] **Step 1: Обновить router/index.js**

```javascript
import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';

function isTokenValid() {
    const token = localStorage.getItem('beecrm_jwt');
    if (!token) return false;
    try {
        const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
        return payload.exp * 1000 > Date.now();
    } catch {
        return false;
    }
}

const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: '/login', component: () => import('@/views/LoginView.vue') },
        { path: '/register', component: () => import('@/views/RegisterView.vue') },
        {
            path: '/',
            component: AppLayout,
            children: [
                { path: '', component: () => import('@/views/DashboardView.vue') },
                { path: 'orders', component: () => import('@/views/OrdersView.vue') },
                { path: 'orders/:id', component: () => import('@/views/OrderDetailView.vue'), props: true },
                { path: 'clients', component: () => import('@/views/ClientsView.vue') },
                { path: 'clients/:id', component: () => import('@/views/ClientDetailView.vue'), props: true },
                { path: 'products', component: () => import('@/views/ProductsView.vue') },
                { path: 'products/:id', component: () => import('@/views/ProductDetailView.vue'), props: true },
            ],
        },
    ],
});

router.beforeEach((to) => {
    if (to.path === '/login' || to.path === '/register') return true;
    if (!isTokenValid()) return '/login';
    return true;
});

export default router;
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/router/index.js
git commit -m "feat(auth): add /register route, guard checks JWT expiry"
```

---

## Task 11: Frontend — реальный username в UI

**Files:**
- Modify: `dashboard/src/layout/AppSidebar.vue`
- Modify: `dashboard/src/layout/AppTopbar.vue`

- [ ] **Step 1: AppSidebar.vue — показать реальный username**

В `<script setup>` уже есть `const auth = useAuthStore()`.

Найти в `<template>`:
```html
<div class="sidebar-user-name">Администратор</div>
<div class="sidebar-user-role">API ключ</div>
```
Заменить на:
```html
<div class="sidebar-user-name">{{ auth.username || 'Пользователь' }}</div>
<div class="sidebar-user-role">{{ auth.role || 'Менеджер' }}</div>
```

Найти:
```html
<div class="sidebar-avatar">A</div>
```
Заменить на:
```html
<div class="sidebar-avatar">{{ (auth.username || 'U')[0].toUpperCase() }}</div>
```

- [ ] **Step 2: AppTopbar.vue — первая буква из username**

В `<script setup>` добавить:
```javascript
import { useAuthStore } from '@/stores/auth.js';
const auth = useAuthStore();
```

Найти:
```html
<div class="topbar-avatar">A</div>
```
Заменить на:
```html
<div class="topbar-avatar">{{ (auth.username || 'U')[0].toUpperCase() }}</div>
```

- [ ] **Step 3: Собрать дашборд**

```bash
cd /home/hive/BEECRM/dashboard && npm run build
```

Ожидаемый вывод: `✓ built in ...` без ошибок.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/layout/AppSidebar.vue dashboard/src/layout/AppTopbar.vue dashboard/dist/
git commit -m "feat(auth): show real username/role/avatar initial in sidebar and topbar"
```

---

## Task 12: Финальный прогон тестов + деплой

- [ ] **Step 1: Полный прогон тестов**

```bash
cd /home/hive/BEECRM && pytest tests/ -v
```

Ожидаемый вывод: все тесты зелёные.

- [ ] **Step 2: Добавить JWT_SECRET в .env на сервере**

```bash
ssh ai-agent@178.253.39.215 "echo 'JWT_SECRET=<сгенерировать_32+_символов>' >> ~/BEECRM/.env"
```

Сгенерировать секрет:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

- [ ] **Step 3: Push и деплой**

```bash
gh auth switch -u alekseymavai && gh auth setup-git
git push origin main
ssh ai-agent@178.253.39.215 "cd ~/BEECRM && git pull && sudo systemctl restart beecrm"
```

- [ ] **Step 4: Smoke-test на продакшне**

```bash
# Регистрация
curl -s -X POST https://usadbadmitrov.ru/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"changeme"}' | python3 -m json.tool

# Логин
curl -s -X POST https://usadbadmitrov.ru/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"changeme"}' | python3 -m json.tool
```

Ожидаемый вывод: `{"access_token":"eyJ...","token_type":"bearer","username":"admin","role":"Менеджер"}`

---

## Self-Review: покрытие требований

| Требование | Задача | Статус |
|-----------|--------|--------|
| Компонент авторизации (логин) | Task 8 (LoginView) | ✅ |
| Компонент регистрации | Task 9 (RegisterView) | ✅ |
| Маршруты /login и /register | Task 10 (router) | ✅ |
| Хранение пользователей в Integram | Task 0 + Task 3 | ✅ |
| JWT вместо API-ключа | Task 3, 4, 6, 7 | ✅ |
| Обратная совместимость X-API-Key | Task 4 | ✅ |
| Best practices (lookup table для ролей) | Task 0 | ✅ |
| Стиль в соответствии с app.css | Task 8, 9 (используют .login-page, .login-box и т.д.) | ✅ |
| Реальный username в UI | Task 11 | ✅ |
| TDD | Task 3, 4 | ✅ |
