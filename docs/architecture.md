# BEECRM — Архитектура

> Обновлено командой AgentForge · 25.04.2026 (миграция на usadba)
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
        Integram API (ai2o.online/usadba)
        ├─ Клиенты (typeId 21)
        ├─ Заказы (typeId 24)
        ├─ История заказов (typeId 28890, child от 24)
        ├─ Статусы (typeId 15, справочник)
        ├─ Источники (typeId 14, справочник)
        └─ Товары (typeId 23)
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
Каждый переход записывается в История заказов (typeId 28890, append-only).

---

## Integram — маппинг (workspace: usadba, обновлено 2026-04-25)

### Справочники

| Таблица | typeId | Значения (record ID) |
|---------|--------|----------|
| Источники | 14 | UDS(122), ВК(123), Instagram(124), Telegram(125), WhatsApp(126), Мессенджер(127), Личное обращение(128), Портал(129) |
| Статусы заказов | 15 | Новый(130), В обработке(131), Собран(132), Отправлен(133), Доставлен(134), Отменён(135) |
| Статусы оплаты | 16 | Оплачен, Не оплачен, Частично оплачен |
| Категории товаров | 17 | Продукты пчеловодства, Настойки, Программы здоровья, Мёд, Наборы, Упаковка, Свечи, Чаи и травы |
| Мессенджеры | 18 | Telegram, WhatsApp, SMS |
| Способы доставки | 19 | СДЭК, Почта России, Самовывоз |
| Уровни лояльности | 20 | (справочник UDS) |

### Товары (typeId 23)

| Поле | colId | Тип | Заметки |
|------|-------|-----|---------|
| Название | value | text | — |
| Цена | 47 | number | — |
| Описание | 50 | memo | — |
| В наличии | 54 | bool | active flag |
| Категория | 81 | ref→17 | — |
| Остаток | — | — | usadba не ведёт остатки (COL_PRODUCT_STOCK=None) |

### Клиенты (typeId 21)

| Поле | colId | Тип | Заметки |
|------|-------|-----|---------|
| Название | value | text | ФИО |
| Телефон | 29 | text | — |
| Email | 30 | text | — |
| UDS ID | 31 | text | — |
| Telegram ID | 32 | text | — |
| Telegram Username | 33 | text | — |
| Баллы | 34 | number | UDS |
| Сумма покупок | 35 | number | UDS |
| Кол-во заказов | 36 | number | — |
| Дата регистрации | 37 | date | — |
| Дата последнего заказа | 38 | date | — |
| Примечание | 39 | memo | — |
| Мессенджер | 78 | ref→18 | — |
| Источник | 79 | ref→14 | — |
| Уровень лояльности | 80 | ref→20 | — |

### Заказы (typeId 24)

| Поле | colId | Тип | Заметки |
|------|-------|-----|---------|
| Номер | 55 | text | — |
| Дата | 56 | date | COL_ORDER_CREATED_AT |
| ФИО получателя | 57 | text | — |
| Телефон получателя | 58 | text | — |
| Адрес доставки | 59 | text | — |
| Сумма | 60 | number (валюта) | COL_ORDER_AMOUNT |
| Проведён в UDS | 61 | bool | — |
| Дата отправки | 62 | date | — |
| Ожидаемая дата доставки | 63 | date | — |
| Трек-номер | 64 | text | — |
| ПВЗ факт | 65 | text | — |
| Вес (кг) | 66 | number | — |
| Длина (см) | 67 | number | — |
| Ширина (см) | 68 | number | — |
| Высота (см) | 69 | number | — |
| Источник | 82 | ref→14 | COL_ORDER_SOURCE |
| Клиент | 83 | ref→21 | COL_ORDER_CLIENT |
| Мессенджер для трека | 84 | ref→18 | — |
| Способ доставки | 85 | ref→19 | — |
| Статус оплаты | 86 | ref→16 | — |
| Статус заказа | 87 | ref→15 | COL_ORDER_STATUS (скрыт в schema, работает) |
| Комментарий | — | — | child-таблица 27 (COL_ORDER_NOTES=None) |

### Товары заказа (typeId 25, child от 24)

| Поле | colId | Тип |
|------|-------|-----|
| Количество | — | number |
| Цена за единицу | — | number |
| Сумма | — | number |
| Товар | — | ref→23 |

### Дозаказы (typeId 26, child от 24)

child-таблица для дозаказов.

### Комментарии (typeId 27, child от 24)

child-таблица для комментариев к заказу.

### Пользователи CRM (typeId 28885)

| Поле | colId | Тип |
|------|-------|-----|
| login | 28886 | text |
| password_hash | 28887 | text |
| role | 28888 | text |
| is_active | 28889 | bool |

### История изменений заказа (typeId 28890, child от 24)

| Поле | colId | Тип |
|------|-------|-----|
| Предыдущий статус | 28891 | text |
| Новый статус | 28892 | text |
| Кто изменил | 28893 | text |
| Описание | 28894 | memo |
| Дата изменения | 28895 | datetime |

### Адреса (typeId 22, child от 21)

child-таблица для адресов клиента.

---

## API (FastAPI)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Проверка доступности сервиса |
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
| GET | `/products/` | Список товаров |
| POST | `/products/` | Создать товар |
| GET | `/products/{id}` | Получить товар |
| PATCH | `/products/{id}` | Обновить товар |
| DELETE | `/products/{id}` | Soft-delete товара (active=False) |
| POST | `/import/excel/preview` | Предпросмотр xlsx-файла (заголовки + первые строки) |
| POST | `/import/excel` | Импорт заказов из xlsx/csv |

---

## Структура файлов

```
BEECRM/
├── CLAUDE.md
├── settings.py              ← секреты из env, startup_check()
├── main.py                  ← FastAPI app, lifespan + IntegramClient.authenticate()
├── integram/
│   ├── client.py            ← async httpx клиент Integram API (+ import_xlsx, T_PRODUCTS)
│   ├── deps.py              ← get_integram() FastAPI Depends
│   ├── mappers.py           ← igm_to_client, igm_to_order, igm_to_product, igm_to_event — конвертация Integram dict → домен
│   └── exceptions.py        ← IntegramError, IntegramNotFoundError
├── schemas/
│   ├── enums.py             ← OrderStatus, OrderSource
│   ├── client.py            ← ClientCreate / ClientRead / ClientUpdate
│   ├── order.py             ← OrderCreate / OrderRead / OrderStatusUpdate / OrderEventRead
│   └── product.py           ← ProductCreate / ProductRead / ProductUpdate
├── adapters/
│   ├── base.py              ← BaseAdapter: normalize() + _validate()
│   ├── uds_adapter.py
│   ├── messenger_adapter.py
│   └── table_adapter.py     ← + from_xlsx_row()
├── services/
│   ├── fsm.py               ← ALLOWED_TRANSITIONS, transition(), FSMError
│   ├── notify_service.py    ← send_new_order_notification() — уведомления команде через BEEBOTLITE
│   ├── order_service.py     ← create_order(), transition_status(), get_history()
│   └── client_service.py    ← find_or_create() (дедупликация) + get_history()
├── api/
│   ├── auth.py              ← verify_api_key (X-API-Key, 403)
│   ├── clients.py
│   ├── orders.py
│   ├── products.py          ← CRUD товаров + soft-delete
│   └── import_excel.py      ← POST /import/excel + /import/excel/preview
├── dashboard/               ← Vue 3 + PrimeVue 4 + Tailwind (отдельный SPA)
│   ├── src/
│   │   ├── api/http.js      ← axios + X-API-Key из localStorage
│   │   ├── stores/          ← Pinia: auth, orders, clients, products
│   │   ├── views/           ← Login, Dashboard, Orders, Clients, Products + Detail views
│   │   └── router/index.js  ← guard: /login если нет ключа
│   └── dist/                ← собранный фронтенд (nginx serving)
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
| `API_KEY` | ✅ | X-API-Key для аутентификации |
| `INTEGRAM_LOGIN` | ✅ | Email аккаунта Integram |
| `INTEGRAM_PASSWORD` | ✅ | Пароль аккаунта Integram |
| `INTEGRAM_WORKSPACE` | — | Slug воркспейса (по умолчанию: `usadba`) |
| `INTEGRAM_T_EVENTS` | — | typeId child-таблицы OrderEvent (по умолчанию: `28890`) |

---

## Инфраструктура (прод)

```
Интернет
    │
    ├─▶ https://usadbadmitrov.ru  (nginx + Certbot TLS → :8000 API)
    ├─▶ http://178.253.39.215:8000  (API прямой доступ)
    └─▶ http://178.253.39.215:8080  (Dashboard Vue SPA, nginx)
              │
              ▼
      systemd: beecrm.service
              │
              ▼
      uvicorn main:app (ai-agent, ~/BEECRM/.venv)
              │
              ▼
      Integram API (ai2o.online/usadba)
```

---

## Открытые блокеры

| # | Блокер | Статус |
|---|--------|--------|
| 1 | HTTP, не HTTPS | ✅ done — nginx + Certbot на usadbadmitrov.ru |
| 2 | CORS жёстко захардкожен в main.py | ✅ done |
| 3 | BASE_url_hardcode | ✅ done (ADR-007) |

## Fragile Zones

| Зона | Риск | Статус |
|------|------|--------|
| `client_dedup` | Дедупликация по phone/email через Integram search | ✅ реализовано |
| `no_transactions` | Integram не поддерживает ACID | ⚠️ compensating actions |
| `uds_sync` | UDS polling: seen_ids in-memory — сбрасывается при рестарте | ⚠️ заказы до рестарта не дедуплицируются |
| `order_addon` | Дозаказ должен добавляться к существующему | ⏳ не реализован |

---

---

## Модуль UDS (polling-интеграция)

> Добавлено AgentForge · 10.04.2026

### Описание

Polling-интеграция UDS-магазина → BEECRM по микроядерному паттерну модуля `apiary/`.
При появлении нового заказа в UDS — создаёт клиента и заказ в BEECRM через `find_or_create` + `create_order`.

**Микроядерный принцип**: модуль изолирован в `uds/`. Ядро (`integram/`, `services/`) не изменялось.

### Принцип работы

```
UDS Admin API (api.uds.app/admin)
    │  polling каждые UDS_POLL_INTERVAL сек
    ▼
UDSPoller._tick()
    ├─ GET /goods-orders (offset=0, limit=50)
    ├─ фильтр: seen_ids (in-memory дедупликация)
    ├─ GET /goods-orders/{id} (детали)
    └─ _process_order()
         ├─ parse_order() → нормализованный dict
         ├─ client_service.find_or_create()
         └─ order_service.create_order(source=UDS)
```

### Маппинг статусов UDS → OrderStatus

| UDS state | OrderStatus |
|-----------|-------------|
| NEW | NEW |
| NEED_ACK | NEW |
| WAITING_PAYMENT | NEW |
| ACCEPTED | CONFIRMED |
| COMPLETED | DONE |
| CANCELLED | CANCELLED |

### API endpoints

| Метод | Путь | Аутентификация | Описание |
|-------|------|---------------|----------|
| GET | `/uds/health` | нет | Статус polling (running, last_poll, error, synced_count) |
| POST | `/uds/poll` | X-API-Key | Ручной триггер одного tick |

### Переменные окружения

| Переменная | Обязательна | Описание |
|------------|-------------|----------|
| `UDS_ADMIN_TOKEN` | рекомендована | Bearer токен (~120 дней), модуль опционален |
| `UDS_COMPANY_ID` | рекомендована | ID компании в UDS |
| `UDS_POLL_INTERVAL` | — | Интервал в секундах (default: 60) |
| `UDS_INITIAL_SYNC` | — | Начальная синхронизация истории (not yet implemented) |

### Структура файлов

```
uds/
├── __init__.py
├── config.py      ← env-переменные, check() — WARNING если не задан
├── client.py      ← UDSAdminClient (httpx), UDSError/UDSAuthError/UDSAPIError
├── mapper.py      ← parse_order(), UDS_STATUS_MAP
├── poller.py      ← UDSPoller: start/stop/status/_tick/_process_order
└── router.py      ← GET /uds/health, POST /uds/poll
```

### Обработка ошибок

- `UDSAuthError` (401/403) → устанавливает `_error`, останавливает loop, не крашит приложение
- Ошибка одного заказа → логирует ERROR, продолжает обработку остальных
- Токен не задан → WARNING при старте, poller запускается но не делает запросов

---

## Модуль Apiary (BEEBOTLITE)

> Добавлено AgentForge · 10.04.2026

### Описание

Telegram-бот пчеловода. Принимает голосовые и текстовые сообщения осмотров ульев,
транскрибирует речь через Groq Whisper, извлекает структурированные данные через Groq LLM
и сохраняет в Integram.

**Микроядерный принцип**: модуль изолирован в `apiary/`. Ядро (`integram/`, `settings.py`) не изменялось.

### Таблицы Integram (создать через `python -m apiary.scripts.create_tables`)

| Таблица | Env APIARY_T_* | Описание |
|---------|---------------|----------|
| Роли пасеки | APIARY_T_ROLES | Справочник: Пчеловод, Старший пчеловод, Администратор |
| Статусы здоровья | APIARY_T_HEALTH | Справочник: Здоров, Требует внимания, Болен, Подозрение |
| Ульи | APIARY_T_HIVES | Объекты пасеки (name, location, is_active) |
| Пользователи бота | APIARY_T_USERS | Telegram-пользователи (tg_id, role, is_active) |
| Осмотры | APIARY_T_INSPECTIONS | Записи осмотров (13 полей + raw_text) |

TypeId заполняются после запуска скрипта `python -m apiary.scripts.create_tables`
и прописываются в `.env` (см. `.env.example` секция BEEBOTLITE).

### Переменные окружения

| Переменная | Обязательна | Описание |
|------------|-------------|----------|
| `BEEBOTLITE_TOKEN` | ✅ | Telegram Bot Token |
| `GROQ_API_KEY` | ✅ | Groq API ключ (STT + LLM) |
| `BEEBOTLITE_ADMIN_TG_ID` | ✅ | Telegram ID администратора |
| `APIARY_T_ROLES` | ✅ | typeId таблицы "Роли пасеки" |
| `APIARY_T_HEALTH` | ✅ | typeId таблицы "Статусы здоровья" |
| `APIARY_T_HIVES` | ✅ | typeId таблицы "Ульи" |
| `APIARY_T_USERS` | ✅ | typeId таблицы "Пользователи бота" |
| `APIARY_T_INSPECTIONS` | ✅ | typeId таблицы "Осмотры" |
| `APIARY_COL_*` | ✅ | col_id всех колонок (см. .env.example) |

### FSM осмотра

```
IDLE
  │ 🐝 Начать осмотр
  ▼
INSPECTION ← голос/текст → Groq Whisper → Groq LLM → Integram
  │
  │ requires_clarification → 1 переспрос → is_draft=True
  │
  │ ✅ Завершить осмотр
  ▼
IDLE (вывод сводки: кол-во записей, ульи требующие внимания)
```

### PRIVACY NOTE

Голосовые и текстовые сообщения уходят в облако Groq (api.groq.com).
raw_text хранится в Integram, в логи не попадает.

### Структура файлов

```
apiary/
├── __init__.py
├── bot.py                   ← точка входа (python -m apiary.bot)
├── config.py                ← env-переменные модуля
├── models.py                ← Pydantic: Hive, ApiaryUser, InspectionRecord
├── prompts.py               ← LLM-промпт извлечения осмотра
├── groq_client.py           ← transcribe() + extract_record()
├── integram_apiary.py       ← CRUD: get_user, create_inspection, get_last_inspections
├── scripts/
│   └── create_tables.py     ← одноразовый скрипт инициализации таблиц
├── routers/
│   ├── start.py             ← /start, главное меню, регистрация
│   ├── inspection.py        ← FSM осмотра
│   └── admin.py             ← /adduser, /addhive, /approve
└── tests/
    ├── conftest.py          ← FakeIntegramClient + env-заглушки
    └── test_inspection.py   ← 5 тестов
```

### Запуск

```bash
# 1. Создать таблицы в Integram (один раз)
python -m apiary.scripts.create_tables

# 2. Прописать typeId и colId в .env

# 3. Запустить бота
python -m apiary.bot

# Или через systemd
sudo cp beebotlite.service /etc/systemd/system/
sudo systemctl enable --now beebotlite
```

*Обновлено AgentForge · 10.04.2026*

---

## Журнал изменений схемы

### 2026-04-25 — Миграция beecrm → usadba (AgentForge полный цикл)

**Контекст:** Перевод BEECRM с тестового workspace `beecrm` на продакшн `usadba` (реальные данные «Усадьба Дмитровых»).

**Что сделано:**
- Полный ремаппинг всех typeId и colId в `integram/client.py`
- Обновлены STATUS_MAP (130–135) и SOURCE_MAP (122–125)
- Созданы 2 новые таблицы в usadba через MCP: Пользователи CRM (28885), История изменений заказа (28890)
- Mappers и API endpoints адаптированы под None-колонки (COL_ORDER_NOTES=None, COL_PRODUCT_STOCK=None)
- FakeIntegramClient наследует все константы из IntegramClient (больше не рассинхронизируется)
- Деплой на VPS 178.253.39.215, .env обновлён, smoke test passed

**Отличия usadba от beecrm:**
- Нет колонки «Комментарий» в заказах — используется child-таблица 27
- Нет колонки «Остаток» в товарах — usadba не ведёт складской учёт
- Есть расширенные поля UDS: ID, баллы, сумма покупок, уровни лояльности
- Есть child-таблицы: Адреса (22), Дозаказы (26), Комментарии (27)

### 2026-04-18 — AgentForge (Ведатель→Зодчий→Делатель→Испытатель→Летописец)

**Контекст:** Анализ соответствия схемы beecrm процессу пчеловода («Усадьба Дмитровых»).

**Ключевые открытия:**
- `alekseymavai/schema` не отображает таблицы (`baseType=1`) — это legacy-тип, недоступный через текущий API/UI
- `beecrm` использует `baseType=3` для всех таблиц — это корректный тип для схема-вью Integram
- `create_table` через MCP всегда создаёт `baseType=3`, параметр `kind/type` отсутствует

**Добавлено в beecrm:**

Новые справочники:
- `Статусы оплаты` (typeId=1533): Оплачен, Не оплачен, Частично оплачен
- `Статусы коммуникации` (typeId=1534): Не связались, Связались, Нет ответа, Не актуален, Дозаказ
- `Предпочтительный мессенджер` (typeId=1532): Telegram, WhatsApp, SMS

Новые колонки в **Заказы** (typeId=20):
- `Источник` (ref→15), `Дата сборки`, `Дата отправки`
- `Вес заказа (кг)`, `Длина (см)`, `Ширина (см)`, `Высота (см)`
- `Статус оплаты` (ref→1533), `Статус коммуникации` (ref→1534)

Новые колонки в **Клиенты** (typeId=19):
- `Предпочтительный мессенджер` (ref→1532)

**Баги Integram API (отправлены разработчику):**
1. `create_table` не поддерживает параметр `kind/type` для создания `baseType=1`
2. Параллельные `create_table` теряют очередь `confirm_action`
3. `delete_object` + `confirm_action` → стабильный 500 Internal Error
