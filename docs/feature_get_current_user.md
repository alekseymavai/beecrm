# Feature: get_current_user() — Двухуровневая аутентификация

**Дата:** 2026-04-16
**Автор:** Claude (Haiku 4.5)
**Статус:** ✅ Завершено и протестировано
**Коммит:** `65798cc`

---

## Описание

Реализована функция `get_current_user()` в `integram/deps.py` для извлечения информации о текущем пользователе из запроса.

Функция поддерживает **двухуровневую аутентификацию**:
1. **Bearer JWT** (приоритет выше) — проверяет `Authorization: Bearer <token>`
2. **X-API-Key fallback** — проверяет заголовок `X-API-Key` для backward compatibility

---

## Зачем это нужно

Раньше маршруты в `api/beelog.py` импортировали несуществующую функцию `get_current_user`:

```python
from integram.deps import get_current_user  # ❌ ImportError

@router.post("/hives")
async def create_hive(
    user: dict = Depends(get_current_user),  # Требовалась функция
    ...
):
```

Это вызывало ошибку при импорте роутера. Теперь функция реализована.

---

## Реализация

### Сигнатура

```python
async def get_current_user(
    authorization: str | None = Header(None),
    api_key: str | None = Security(_header_scheme),
) -> dict:
    """
    Returns:
        {"username": str, "role": str}

    Raises:
        HTTPException(401): Если нет валидной аутентификации
    """
```

### Логика (ВАРИАНТ B)

```
┌─────────────────────────────┐
│   get_current_user()        │
└──────────────┬──────────────┘
               │
        ┌──────▼──────┐
        │ JWT TokenReady?
        └──────┬───────┘
         YES  │  NO
             │
        ┌────▼─────┐         ┌──────────────┐
        │ Decode & │         │  X-API-Key   │
        │ Return   │◄────────│  Valid?      │
        │ username,│    YES  └──────────────┘
        │ role     │              │ NO
        └──────────┘              │
                                  ▼
                            HTTPException(401)
                          "Требуется аутентификация"
```

### JWT Payload

```python
{
    "sub": "username",           # обязательно
    "role": "Собственник",       # опционально, default="Менеджер"
    "exp": <unix_timestamp>      # обязательно
}
```

### X-API-Key Response

```python
{
    "username": "api",
    "role": "API"
}
```

---

## Тесты

**Файл:** `tests/test_deps.py`
**Количество тестов:** 11
**Статус:** ✅ 11/11 ЗЕЛЁНЫЕ

### Покрытие

| Сценарий | Тест | Результат |
|----------|------|-----------|
| JWT с ролью | `test_valid_jwt_returns_user_with_role` | ✅ |
| JWT без роли (default) | `test_jwt_without_role_defaults_to_manager` | ✅ |
| Невалидный JWT → X-API-Key | `test_invalid_jwt_falls_back_to_api_key` | ✅ |
| Истекший JWT → X-API-Key | `test_expired_jwt_falls_back_to_api_key` | ✅ |
| Валидный X-API-Key | `test_valid_api_key_returns_api_user` | ✅ |
| Невалидный X-API-Key | `test_invalid_api_key_raises_401` | ✅ |
| Отсутствует аутентификация | `test_no_auth_headers_raises_401` | ✅ |
| Bearer без префикса → fallback | `test_bearer_prefix_required` | ✅ |
| POST /beelog/hives с JWT | `test_beelog_hives_endpoint_with_jwt` | ✅ |
| POST /beelog/hives с X-API-Key | `test_beelog_hives_endpoint_with_api_key` | ✅ |
| POST /beelog/hives без auth | `test_beelog_hives_endpoint_no_auth` | ✅ |

---

## Безопасность

✅ **Аудит OWASP:**
- ✅ `hmac.compare_digest()` — защита от timing attacks
- ✅ `try/except JWTError` — корректная обработка ошибок JWT
- ✅ `HTTPException(401)` — не разкрывает деталей
- ✅ Bearer token проверяется перед X-API-Key (нет privilege escalation)
- ✅ Пароль не логируется

---

## Использование в коде

### В маршрутах

```python
from fastapi import Depends
from integram.deps import get_current_user

@router.post("/hives")
async def create_hive(
    body: HiveCreate,
    user: dict = Depends(get_current_user),
    igm: IntegramClient = Depends(get_integram),
):
    if user.get("role") != "Собственник":
        raise HTTPException(status_code=403, detail="Только собственник может создавать ульи")
    # ... rest of logic
```

### Клиент-сайд (JavaScript/Python)

**Вариант 1: JWT**
```javascript
const token = "eyJ0eXAiOiJKV1QiLCJhbGc...";
const response = await fetch("/beelog/hives", {
    method: "POST",
    headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
    },
    body: JSON.stringify({ number: "UL-001" })
});
```

**Вариант 2: X-API-Key (backward compatibility)**
```javascript
const response = await fetch("/beelog/hives", {
    method: "POST",
    headers: {
        "X-API-Key": "test-api-key",
        "Content-Type": "application/json"
    },
    body: JSON.stringify({ number: "UL-001" })
});
```

---

## Файлы изменены

```
integram/deps.py           [+45 lines] Добавлена get_current_user()
main.py                    [+2 lines]  Добавлен beelog_router в app
tests/test_deps.py         [+230 lines] Новый файл с 11 тестами
```

---

## Следующие шаги

1. ✅ Деплой на продакшн (178.253.39.215)
2. ✅ Verify endpoints: POST /beelog/hives, /inspections
3. ✅ Мониторинг логов
