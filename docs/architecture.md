# BEECRM — Архитектура

> Обновлено командой AgentForge · 08.04.2026
> ADR-001: FastAPI + Integram API (хранилище)

---

## Телос

CRM-система для пчеловода Александра Дмитрова («Усадьба Дмитровых»).
Принимает заказы из нескольких источников, управляет жизненным циклом, хранит клиентскую базу с историей.

---

## Архитектура

```
UDS / Telegram / WhatsApp / Vue Dashboard
              │
              ▼
        BEECRM API (FastAPI)
        ├─ Адаптеры (нормализация входящих данных)
        ├─ FSM (контроль переходов статусов)
        ├─ Дедупликация клиентов
        └─ X-API-Key аутентификация
              │
              ▼
        Integram API (ai2o.online/beecrm)
        ├─ Клиенты (typeId 16)
        ├─ Заказы (typeId 17)
        ├─ История заказов (typeId 37, child от 17)
        ├─ Статусы (typeId 14, справочник)
        └─ Источники (typeId 15, справочник)
```

---

## Источники → Адаптеры

```
UDS          Мессенджер (TG/WA)    Таблица (Excel/Google)
 │                  │                       │
 ▼                  ▼                       ▼
UDSAdapter   MessengerAdapter         TableAdapter
         └───────────┴───────────────────┘
                         │
              BaseAdapter.normalize(raw)
              (forbidden keys, trim >2048, ≤64KB)
                         │
                         ▼
              POST /orders/from-source
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
 └─────────────────────────→ CANCELLED
```

Матрица допустимых переходов — `services/fsm.py`.
Каждый переход записывается в История заказов (typeId 37, append-only).

---

## Integram — маппинг

### Статусы (typeId 14)

| OrderStatus | Integram | objId |
|-------------|---------|-------|
| NEW         | Новый   | 18    |
| CONFIRMED   | Подтверждён | 190 |
| IN_PROGRESS | В работе | 19   |
| DONE        | Выполнен | 20   |
| CANCELLED   | Отменён  | 21   |

### Источники (typeId 15)

| OrderSource | Integram | objId |
|-------------|---------|-------|
| UDS         | UDS      | 22    |
| MESSENGER   | Telegram | 23    |
| TABLE       | Сайт     | 25    |

### Клиенты (typeId 16)

| Поле  | col ID |
|-------|--------|
| name  | —      |
| phone | 28     |
| email | 29     |
| notes | 27     |

### Заказы (typeId 17)

| Поле       | col ID |
|------------|--------|
| client_id  | 30 (ref→16) |
| status     | 31 (ref→14) |
| source     | 32 (ref→15) |
| payload    | 34 (memo, JSON) |
| amount     | 33     |
| created_at | 35     |

### История заказов (typeId 37, child от 17)

| Поле        | col ID |
|-------------|--------|
| from_status | 38     |
| to_status   | 39     |
| actor       | 40     |
| meta        | 41     |
| created_at  | 42     |

---

## API (FastAPI)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/clients/` | Создать клиента |
| GET | `/clients/` | Список клиентов |
| GET | `/clients/{id}` | Получить клиента |
| PATCH | `/clients/{id}` | Обновить клиента |
| GET | `/clients/{id}/history` | История заказов клиента |
| POST | `/orders/` | Создать заказ |
| GET | `/orders/` | Список заказов |
| GET | `/orders/{id}` | Получить заказ |
| PATCH | `/orders/{id}/status` | Сменить статус (FSM) |
| GET | `/orders/{id}/history` | История переходов заказа |
| POST | `/orders/from-source` | Принять заказ из источника через адаптер |

---

## Структура файлов

```
BEECRM/
├── CLAUDE.md
├── context.yaml
├── settings.py              ← секреты из env, startup_check()
├── main.py                  ← FastAPI app, lifespan + IntegramClient.authenticate()
├── integram/
│   ├── client.py            ← async httpx клиент Integram API
│   ├── deps.py              ← get_integram() FastAPI Depends
│   ├── mappers.py           ← dict → Pydantic схемы
│   └── exceptions.py        ← IntegramError, IntegramNotFoundError
├── schemas/
│   ├── enums.py             ← OrderStatus, OrderSource
│   ├── client.py            ← ClientCreate / ClientRead / ClientUpdate
│   └── order.py             ← OrderCreate / OrderRead / OrderStatusUpdate
├── adapters/
│   ├── base.py              ← BaseAdapter: normalize() + _validate()
│   ├── uds_adapter.py
│   ├── messenger_adapter.py
│   └── table_adapter.py     ← + from_xlsx_row()
├── services/
│   ├── fsm.py               ← ALLOWED_TRANSITIONS, transition(), FSMError
│   ├── order_service.py     ← create_order(), transition_status(), get_history()
│   └── client_service.py    ← find_or_create() (дедупликация)
├── api/
│   ├── auth.py              ← verify_api_key (X-API-Key, 403)
│   ├── clients.py
│   └── orders.py
├── tests/
│   ├── conftest.py          ← FakeIntegramClient + dependency_override
│   ├── mocks/
│   │   └── integram_mock.py ← in-memory имитация Integram
│   ├── test_adapters.py
│   ├── test_client_service.py
│   ├── test_order_service.py
│   └── test_api_from_source.py
├── docs/
│   ├── architecture.md
│   └── plan.md
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Переменные окружения (.env)

| Переменная | Обязательна | Описание |
|------------|-------------|----------|
| `SECRET_KEY` | ✅ | Секретный ключ приложения |
| `API_KEY` | ✅ | X-API-Key для аутентификации |
| `INTEGRAM_LOGIN` | ✅ | Email аккаунта Integram |
| `INTEGRAM_PASSWORD` | ✅ | Пароль аккаунта Integram |
| `INTEGRAM_WORKSPACE` | — | Slug воркспейса (по умолчанию: `beecrm`) |
| `INTEGRAM_T_EVENTS` | — | typeId child-таблицы OrderEvent (по умолчанию: `37`) |

---

## Инфраструктура (прод)

```
Интернет
    │
    ├─▶ http://178.253.39.215:8000  (прямой доступ)
    └─▶ http://api.ai2o.online      (nginx proxy, ждём DNS → потом HTTPS)
              │
              ▼
      nginx → 127.0.0.1:8000
              │
              ▼
      systemd: beecrm.service
              │
              ▼
      uvicorn main:app (ai-agent, ~/BEECRM/.venv)
              │
              ▼
      Integram API (ai2o.online/beecrm)
```

---

## Открытые блокеры

| # | Блокер | Статус |
|---|--------|--------|
| 1 | HTTP, не HTTPS | ⏳ ждём DNS api.ai2o.online → 178.253.39.215 |

## Fragile Zones

| Зона | Риск | Статус |
|------|------|--------|
| `client_dedup` | Дедупликация по phone/email через Integram search | ✅ реализовано |
| `no_transactions` | Integram не поддерживает ACID | ⚠️ compensating actions |
| `uds_sync` | Нет официального UDS API | ⏳ не начато |
| `order_addon` | Дозаказ должен добавляться к существующему | ⏳ не начато |

---

*Обновлено AgentForge · 08.04.2026*
