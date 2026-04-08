# BEECRM — Архитектура

> Обновлено командой AgentForge (Scout → Architect → Security)
> Дата: 08.04.2026 · Security: RED (см. открытые блокеры)
> ADR-001: FastAPI + SQLAlchemy + PostgreSQL

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
                    (forbidden keys, trim >2048, ≤64KB)
                                   │
                                   ▼
                    POST /orders/from-source  ← ещё не реализован
                                   │
                    client_service.find_or_create()
                                   │
                    order_service.create_order()
```

**Правило безопасности:** сырые данные не могут покинуть слой адаптеров
без прохождения `BaseAdapter.normalize()`.

---

## Жизненный цикл заказа (FSM)

```
  NEW → CONFIRMED → IN_PROGRESS → DONE
   └──────────────────────────→ CANCELLED
```

Матрица допустимых переходов — `services/fsm.py`.
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
from_status  (NULL = событие создания)
to_status
actor
meta JSONB
created_at
[INSERT ONLY — UPDATE/DELETE запрещены на уровне сервиса]
```

---

## API (FastAPI) — текущее состояние

| Метод | Путь | Статус | Описание |
|-------|------|--------|----------|
| POST | `/clients/` | ✅ | Создать клиента |
| GET | `/clients/` | ✅ | Список клиентов |
| GET | `/clients/{id}` | ✅ | Получить клиента |
| PATCH | `/clients/{id}` | ✅ | Обновить клиента |
| GET | `/clients/{id}/history` | ❌ план | История заказов клиента |
| POST | `/orders/` | ⚠️ | Создать заказ (обходит order_service — нет OrderEvent) |
| GET | `/orders/` | ✅ | Список заказов |
| GET | `/orders/{id}` | ✅ | Получить заказ |
| PATCH | `/orders/{id}/status` | ✅ | Сменить статус (FSM) |
| GET | `/orders/{id}/history` | ❌ план | История переходов заказа |
| POST | `/orders/from-source` | ❌ план | Принять заказ из источника через адаптер |

---

## Структура файлов (факт)

```
BEECRM/
├── CLAUDE.md                ← правила работы в проекте
├── context.yaml             ← AgentForge контекст, телос, fragile zones
├── settings.py              ← секреты из env, startup_check()
├── db.py                    ← SQLAlchemy engine + get_session()
├── main.py                  ← FastAPI app, lifespan
├── models/
│   ├── client.py            ← Client
│   ├── order.py             ← Order + OrderSource + OrderStatus
│   └── order_event.py       ← OrderEvent (append-only)
├── schemas/
│   ├── client.py            ← ClientCreate / ClientRead / ClientUpdate
│   └── order.py             ← OrderCreate / OrderRead / OrderStatusUpdate
├── adapters/
│   ├── base.py              ← BaseAdapter: normalize() + _validate()
│   ├── uds_adapter.py       ← UDSAdapter
│   ├── messenger_adapter.py ← MessengerAdapter
│   └── table_adapter.py     ← TableAdapter + from_xlsx_row()
├── services/
│   ├── fsm.py               ← матрица переходов, transition(), FSMError
│   ├── order_service.py     ← create_order(), transition_status(), get_history()
│   └── client_service.py    ← find_or_create() (дедупликация), get_history()
├── api/
│   ├── clients.py           ← APIRouter /clients
│   └── orders.py            ← APIRouter /orders  ⚠️ требует рефактора
├── migrations/
│   └── versions/
│       └── 0001_initial.py  ← clients, orders, order_events + CHECK payload
├── tests/
│   ├── conftest.py          ← SQLite in-memory + патч JSONB→JSON
│   ├── test_adapters.py     ← 8 тестов (normalize + Security)
│   ├── test_client_service.py ← 6 тестов (дедупликация, fragile zone HIGH)
│   └── test_order_service.py  ← 8 тестов (FSM + история)
├── docs/
│   └── architecture.md      ← этот файл
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

---

## Инфраструктура (прод)

```
Интернет
    │
    ▼ порт 8000 (HTTP — временно, нужен HTTPS)
vm4115781.firstbyte.club (178.253.39.215)
    │
    ▼
systemd: beecrm.service
    │
    ▼
uvicorn main:app (ai-agent, ~/BEECRM/.venv)
    │
    ▼
PostgreSQL 14 (localhost:5432, db: beecrm)
```

---

## Открытые блокеры (Security RED)

| # | Блокер | Решение | Этап |
|---|--------|---------|------|
| 1 | Нет аутентификации — API открыт для всех | `X-API-Key` заголовок | 2 |
| 2 | HTTP, не HTTPS — данные клиентов открытым текстом | nginx + Let's Encrypt | 3 |
| 3 | `POST /orders/` не пишет OrderEvent — история неполная | рефактор через `order_service` | 1 |

## Открытые задачи (не блокируют)

| # | Задача | Этап |
|---|--------|------|
| 4 | `GET /orders/{id}/history` и `GET /clients/{id}/history` | 1 |
| 5 | `POST /orders/from-source` — единая точка входа через адаптер | 4 |
| 6 | Импорт из Excel / Google Таблицы | 5 |
| 7 | Уведомления клиентам (Telegram/WhatsApp) | 6 |

---

## Fragile Zones (из context.yaml)

| Зона | Риск | Статус |
|------|------|--------|
| `client_dedup` | UDS + мессенджер — один клиент | ✅ реализовано в `client_service.find_or_create()` |
| `uds_sync` | Нет официального UDS API | ⏳ не начато |
| `cdek_address` | Клиенты дают домашний адрес вместо СДЭК | ⏳ не начато |
| `order_addon` | Дозаказ должен добавляться к существующему | ⏳ не начато |

---

*Обновлено AgentForge · Scout → Architect → Security · 08.04.2026*
