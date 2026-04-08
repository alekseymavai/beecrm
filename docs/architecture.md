# BEECRM — Архитектура

> Согласовано командой AgentForge (Scout → Architect → Security)
> Дата: 08.04.2026 · Security: YELLOW ACCEPTED
> ADR-001: Вариант A — FastAPI + SQLAlchemy + PostgreSQL

---

## Телос

CRM-система для пчеловода Александра Дмитрова («Усадьба Дмитровых»).
Принимает заказы из трёх источников, управляет жизненным циклом, хранит клиентскую базу с историей.
BEEBOT — smart frontend (Telegram-бот), BEECRM — backend-центр данных.

---

## Источники заказов → Адаптеры

```
  UDS (интернет-магазин)   Мессенджер (TG/WA)   Таблица (Google/Excel)
          │                        │                      │
          ▼                        ▼                      ▼
   UDSAdapter              MessengerAdapter         TableAdapter
          │                        │                      │
          └────────────────────────┴──────────────────────┘
                                   │
                    BaseAdapter.normalize(raw)
                           │
                    Pydantic-схема
                    (allowed_keys, max_length, ≤64KB)
                           │
                           ▼
                      OrderService
```

**Правило безопасности:** `BaseAdapter.normalize()` — template method.
Сырые данные физически не могут покинуть слой адаптеров без прохождения Pydantic-схемы.

---

## Жизненный цикл заказа (FSM)

```
  NEW → CONFIRMED → IN_PROGRESS → DONE
   └──────────────────────────→ CANCELLED
```

Матрица допустимых переходов в `services/fsm.py`.
Каждый переход записывается в `order_events` (append-only, только INSERT).

---

## Модели (PostgreSQL)

```
clients                          orders
────────────────────             ────────────────────────────
id                               id
phone  ─┐                        client_id FK → clients
email  ─┴─ UNIQUE                source: UDS | MESSENGER | TABLE
name                             status: NEW | CONFIRMED | IN_PROGRESS | DONE | CANCELLED
created_at                       payload JSONB
updated_at                         CHECK octet_length(payload::text) <= 65536
                                 created_at
                                 updated_at

order_events (append-only)
────────────────────────────────
id
order_id FK → orders
from_status
to_status
actor
meta JSONB
created_at
[INSERT ONLY — UPDATE/DELETE запрещены]
```

---

## API (FastAPI)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/orders` | Создать заказ (source + raw_data + client_id) |
| GET | `/orders/{id}` | Получить заказ |
| PATCH | `/orders/{id}/status` | Сменить статус (FSM, недопустимый → 422) |
| GET | `/orders` | Список с фильтрами: source / status / client |
| POST | `/clients` | Создать клиента (или найти по phone+email) |
| GET | `/clients/{id}` | Клиент |
| PUT | `/clients/{id}` | Обновить клиента |
| GET | `/clients/{id}/history` | История заказов + события |

---

## Конфигурация и безопасность (ADR-001)

```python
# settings.py — все секреты ТОЛЬКО из os.environ, без fallback
DB_URL     = os.environ["DB_URL"]      # KeyError если не задан
SECRET_KEY = os.environ["SECRET_KEY"]
MAX_PAYLOAD_BYTES = 65536              # единственный источник лимита

def startup_check():
    for key in REQUIRED_VARS:
        if key not in os.environ:
            raise ValueError(f"Обязательная переменная не задана: {key}")
```

**Правила:**
1. Секреты — только `os.environ[KEY]`, никаких `.get(KEY, default)`
2. `startup_check()` вызывается при старте приложения
3. `MAX_PAYLOAD_BYTES` импортируется и в Pydantic-схему и в миграцию — один источник правды
4. `order_events` — append-only на уровне сервиса; в будущем добавить PostgreSQL RULE

---

## Структура файлов

```
BEECRM/
├── settings.py              ← секреты из env, startup_check()
├── db.py                    ← SQLAlchemy engine + SessionLocal
├── main.py                  ← FastAPI app, lifespan + роутеры
├── models/
│   ├── client.py            ← Client: id, phone, email, name
│   ├── order.py             ← Order: id, client_id, source, status, payload JSONB
│   └── order_event.py       ← OrderEvent append-only
├── schemas/
│   ├── payload_mixin.py     ← PayloadSizeMixin (64KB, json.dumps separators=(',',':'))
│   ├── order_schema.py      ← UDSPayloadSchema, MessengerPayloadSchema, TablePayloadSchema
│   └── client_schema.py     ← ClientCreateSchema, ClientUpdateSchema
├── adapters/
│   ├── base_adapter.py      ← BaseAdapter: normalize() = _parse() → schema.validate()
│   ├── uds_adapter.py       ← UDSAdapter(BaseAdapter)
│   ├── messenger_adapter.py ← MessengerAdapter(BaseAdapter)
│   └── table_adapter.py     ← TableAdapter: openpyxl с read_only=True, data_only=True
├── services/
│   ├── fsm.py               ← OrderFSM: матрица переходов, transition()
│   ├── order_service.py     ← create_order(), transition_status(), get_history()
│   └── client_service.py    ← find_or_create(), get_history(), update()
├── api/
│   ├── orders.py            ← APIRouter /orders
│   └── clients.py           ← APIRouter /clients
├── migrations/
│   └── versions/
│       └── 0001_initial.py  ← таблицы + CHECK octet_length(payload::text) <= 65536
├── tests/
│   ├── conftest.py          ← fixtures (+ отдельный интеграционный тест на реальном PG)
│   ├── test_adapters.py     ← normalize(): валидный / >64KB / forbidden keys
│   ├── test_schemas.py      ← PayloadSizeMixin unit-тесты
│   ├── test_order_service.py← FSM: корректные и запрещённые переходы
│   └── test_client_service.py← дедупликация: один клиент из двух источников
├── docs/
│   └── architecture.md      ← этот файл
├── context.yaml             ← AgentForge контекст
├── .env.example             ← все обязательные переменные (без значений)
└── requirements.txt
```

---

## Открытые вопросы (Security MEDIUM — не блокируют)

| # | Проблема | Где | Решение |
|---|----------|-----|---------|
| 1 | CHECK constraint не покрыт тестами (SQLite отключает его) | tests/conftest.py | Добавить интеграционный тест на testcontainers PostgreSQL |
| 2 | `json.dumps()` vs `octet_length()` могут давать разный размер | payload_mixin.py | Фиксировать `separators=(',', ':'), ensure_ascii=False` |
| 3 | `startup_check()` может быть подавлен при импорте в тестах | db.py | Дополнительный вызов в `lifespan` hook `main.py` |
| 4 | `.env` может попасть в git | .gitignore | Добавить `detect-secrets` pre-commit hook |

---

*Сгенерировано AgentForge · Scout → Architect → Security · 08.04.2026*
