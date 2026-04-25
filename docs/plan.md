# BEECRM — План работы команды

> Ведётся командой AgentForge. Обновлять после каждого этапа.
> Integram workspace: usadba (ai2o.online)

---

## Статус этапов

| Этап | Задача | Статус |
|------|--------|--------|
| 1 | Рефактор `api/orders` через `order_service` + `GET /*/history` | ✅ done |
| 2 | API Key аутентификация (`X-API-Key`, 403) | ✅ done |
| 3 | HTTPS — nginx + Let's Encrypt для `usadbadmitrov.ru` | ✅ done — Certbot, nginx (11.04.2026) |
| 4 | `POST /orders/from-source` — единая точка входа через адаптер | ✅ done |
| 5 | Рефакторинг хранилища: PostgreSQL → Integram API | ✅ done |
| 6 | Дашборд (Vue 3 + PrimeVue 4) | ✅ done — Login, Dashboard, Orders, Clients, Products |
| 7 | Импорт заказов из Excel / Google Таблицы | ✅ done — POST /import/excel + /preview |
| 8 | Товары (Products API) | ✅ done — CRUD + soft-delete |
| 9 | Уведомления команде пчеловода (BEEBOTLITE) | ✅ done — NotifyService, рассылка активным пользователям APIARY_T_USERS, fallback на ADMIN_TG_ID, 8 тестов (10.04.2026) |
| 10 | UDS интеграция (polling, модуль uds/) | ✅ done — polling, mapper, poller, router, 14 тестов (10.04.2026) |
| 11 | Дозаказ: добавлять к существующему заказу | 📋 todo |
| 12 | HTTPS + CORS из env | ✅ done — CORS_ORIGINS из .env (волна 1, 09.04.2026) |
| 13 | Пагинация client_history (сейчас загружает все заказы в память) | ✅ done — серверный фильтр + пагинация (волна 1, 09.04.2026) |
| 14 | BEEBOTLITE — Telegram бот пчеловода (модуль apiary/) | ✅ done — FSM осмотра, Groq STT+LLM, 5 тестов (10.04.2026) |

---

## Спринт аудита 09.04.2026 (AgentForge)

| Задача | Волна | Статус |
|--------|-------|--------|
| CRITICAL: client_history серверный фильтр | 1 | ✅ done |
| HIGH: CORS_ORIGINS из env | 1 | ✅ done |
| HIGH: IntegramClient.BASE из INTEGRAM_WORKSPACE | 1 | ✅ done |
| HIGH: INTEGRAM_T_EVENTS default=37 | 1 | ✅ done |
| MEDIUM: import_excel Depends() | 1 | ✅ done |
| MEDIUM: SECRET_KEY — мёртвый код убран | 1 | ✅ done |
| HIGH: Rate limiting /import/excel | 2 | ✅ done |
| LOW: hmac.compare_digest в auth.py | 2 | ✅ done |
| LOW: MIME-type валидация загрузки | 2 | ✅ done |
| LOW: Тесты Products API | 3 | ✅ done — 11 тестов |
| LOW: Тесты Import API | 3 | ✅ done — 6 тестов |
| MEDIUM: context.yaml — удалить устаревший | 4 | ✅ done — удалён (PostgreSQL/IP устарели) |
| LOW: dashboard/dist/ в .gitignore | 4 | ✅ done — явная запись добавлена |

---

## Следующий шаг

**Этап 11 — Дозаказ:**
- Добавлять позиции к существующему заказу
- API эндпоинт + логика FSM

**Этап 3 — HTTPS:** ✅ done (11.04.2026)
- Certbot + nginx на `usadbadmitrov.ru` / `www.usadbadmitrov.ru`
- SSL сертификат активен, proxy_pass → 127.0.0.1:8000

---

## Принятые решения (ADR)

| ID | Решение | Статус |
|----|---------|--------|
| ADR-001 | FastAPI + Integram API как хранилище (PostgreSQL убран) | accepted |
| ADR-002 | X-API-Key аутентификация | accepted |
| ADR-003 | Integram workspace `usadba` — Клиенты/Заказы/История (мигрировано с beecrm 25.04.2026) | accepted |
| ADR-004 | Soft-delete для товаров (active=False) вместо физического удаления | accepted |
| ADR-005 | Dashboard — отдельный SPA (Vue 3), API-ключ в localStorage | accepted |
| ADR-006 | Import fallback: сначала Integram import API, потом openpyxl построчно | accepted |
| ADR-007 | IntegramClient.BASE строится из INTEGRAM_WORKSPACE, передаётся в authenticate() | accepted |
| ADR-008 | SECRET_KEY удалён из REQUIRED_VARS — не используется в коде, мёртвый код | accepted |
| ADR-009 | Rate limiting без внешних зависимостей — in-process dict с TTL окном | accepted |
| ADR-010 | NotifyService — Bot создаётся один раз в lifespan, передаётся в UDSPoller через конструктор; ошибка уведомления не прерывает создание заказа | accepted |

---

## Уроки команды

| Урок | Severity |
|------|----------|
| SQLite `:memory:` + FastAPI TestClient требует `StaticPool` | medium |
| `postgresql.ENUM(create_type=False)` в `create_table`, не `sa.Enum` | medium |
| FakeIntegramClient (in-memory dict) — правильный подход для тестов без реального Integram | medium |
| Integram не поддерживает ACID: event создаётся до обновления статуса (compensating actions) | high |
| `redirect_slashes=False` в FastAPI обязателен при nginx proxy (иначе 307 редиректы ломают PUT/PATCH) | medium |
| Import endpoint должен использовать `Depends(get_integram)`, а не `get_integram(request)` напрямую | medium |
| CORS_ORIGINS должны быть в .env — хардкод IP затрудняет смену окружения | high |

---

## Спринт аудита 13.04.2026

AgentForge sprint — post-audit fixes по результатам глубокого аудита архитектуры.

| # | Задача | Тип | Статус |
|---|--------|-----|--------|
| 1 | Убрать reverse import apiary из services/notify_service.py | ARCH | ✅ done |
| 2 | DI recipient_provider в NotifyService | ARCH | ✅ done |
| 3 | Добавить get_active_user_tg_ids() в apiary/integram_apiary.py | PERF | ✅ done |
| 4 | apiary/config.py — заменить os.environ[] на .get() + check() | SEC | ✅ done |
| 5 | groq_client.py — убрать raw_text из логов | SEC | ✅ done |
| 6 | uds/poller.status() — скрыть детали ошибок (bool вместо строки) | SEC | ✅ done |
| 7 | settings.py — токены уже безопасны (os.environ.get), задокументировано | SEC | ✅ n/a |
| 8 | Создать tests/test_mappers.py — 41 тест для integram/mappers.py | TEST | ✅ done |
| 9 | Создать tests/test_auth.py — тесты аутентификации API | TEST | ✅ done |
| 10 | Обновить docs/architecture.md | DOCS | ✅ done |
| 11 | Создать README.md | DOCS | ✅ done |

**Итог:** 113 тестов (было 70 до спринта), 0 регрессий.

### ADR-011 — DI для recipient_provider в NotifyService

**Проблема:** services/notify_service.py импортировал apiary.config напрямую — ядро зависело от плагина.

**Решение:** NotifyService принимает `recipient_provider: Callable | None` через конструктор. В main.py передаётся `get_active_user_tg_ids` из apiary/integram_apiary.py. При `recipient_provider=None` — fallback на admin_tg_id.

**Статус:** accepted

### ADR-012 — Миграция на workspace usadba

**Проблема:** Workspace `beecrm` содержал только тестовые данные. Продакшн-данные находились в `usadba`.

**Решение:** Полный ремаппинг typeId/colId в `integram/client.py`. Константы прибиты к usadba (Вариант A — прямая замена). FakeIntegramClient наследует все константы из IntegramClient для автоматической синхронизации. Колонки отсутствующие в usadba (COL_ORDER_NOTES, COL_PRODUCT_STOCK) установлены в None, код обрабатывает None корректно.

**Статус:** accepted (25.04.2026)
