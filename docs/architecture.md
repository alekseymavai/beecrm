# BEECRM — Архитектура

> Обновлено командой AgentForge · 13.04.2026
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
        ├─ Источники (typeId 15, справочник)
        └─ Товары (typeId 52, справочник)
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

## Integram — маппинг (workspace: beecrm, обновлено 2026-04-18)

### Справочники

| Таблица | typeId | Значения |
|---------|--------|----------|
| Статусы заказов | 14 | Новый(61), Подтверждён(62), В сборке(63), Отправлен(64), Доставлен(65), Отменён(66), Завершен(67) |
| Источники | 15 | ВК(68), Instagram(69), Telegram(70), WhatsApp(71), UDS(72), Личное обращение(73), Сообщество(74) |
| Способы доставки | 16 | СДЭК(75), Почта России(76), Самовывоз(77) |
| Категории товаров | 17 | Продукты пчеловодства(78), Настойки(79), Программы здоровья(80), Мёд(81), Наборы(82), Упаковка(83), Свечи(84), Чаи и травы(85) |
| Статусы оплаты | 1533 | Оплачен(1540), Не оплачен(1543), Частично оплачен(1544) |
| Статусы коммуникации | 1534 | Не связались(1541), Связались(1545), Нет ответа(1546), Не актуален(1547), Дозаказ(1548) |
| Предпочтительный мессенджер | 1532 | Telegram(1538), WhatsApp(1539), SMS(1542) |

### Товары (typeId 18)

| Поле | Alias | Тип |
|------|-------|-----|
| Название | Название | text |
| Цена | Цена | number |
| Вес | Вес | number |
| Описание | Описание | text |
| В наличии | В наличии | bool |
| Артикул UDS | Артикул UDS | text |
| Короткое название | Короткое название | text |
| Остаток | Остаток | number |
| Категория | Категория | ref→17 |

### Клиенты (typeId 19)

| Поле | Alias | Тип |
|------|-------|-----|
| Название | Название | text |
| Телефон | Телефон | text |
| Telegram ID | Telegram ID | text |
| Telegram Username | Telegram Username | text |
| Адрес | Адрес | text |
| Город | Город | text |
| Комментарий | Комментарий | text |
| Предпочтительный мессенджер | Предпочтительный мессенджер | ref→1532 |

### Заказы (typeId 20)

| Поле | Alias | Тип |
|------|-------|-----|
| Номер | Номер | text |
| Дата | Дата | date |
| Адрес доставки | Адрес доставки | text |
| Трек-номер | Трек-номер | text |
| Сумма товаров | Сумма товаров | number |
| Стоимость доставки | Стоимость доставки | number |
| Итого | Итого | number |
| Комментарий | Комментарий | text |
| Состав изменён | Состав изменён | bool |
| Версия состава | Версия состава | number |
| Клиент | Клиент | ref→19 |
| Статус | Статус | ref→14 |
| Способ доставки | Способ доставки | ref→16 |
| Источник | Источник | ref→15 |
| Дата сборки | Дата сборки | date |
| Дата отправки | Дата отправки | date |
| Вес заказа (кг) | Вес заказа (кг) | number |
| Длина (см) | Длина (см) | number |
| Ширина (см) | Ширина (см) | number |
| Высота (см) | Высота (см) | number |
| Статус оплаты | Статус оплаты | ref→1533 |
| Статус коммуникации | Статус коммуникации | ref→1534 |

### Позиции заказа (typeId 21, child от 20)

| Поле | Alias | Тип |
|------|-------|-----|
| Количество | Количество | number |
| Цена за единицу | Цена за единицу | number |
| Сумма | Сумма | number |
| UDS ID товара | UDS ID товара | text |
| Товар | Товар | ref→18 |

### История изменений заказа (typeId 22, child от 20)

| Поле | Alias | Тип |
|------|-------|-----|
| Дата изменения | Дата изменения | date |
| Описание изменения | Описание изменения | text |
| Статус на момент изменения | Статус заказа на момент изменения | text |
| Кто изменил | Кто изменил | text |

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
| `INTEGRAM_WORKSPACE` | — | Slug воркспейса (по умолчанию: `beecrm`) |
| `INTEGRAM_T_EVENTS` | — | typeId child-таблицы OrderEvent (по умолчанию: `37`) |

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
      Integram API (ai2o.online/beecrm)
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
