# BEECRM — План работы команды

> Ведётся командой AgentForge. Обновлять после каждого этапа.
> Integram workspace: beecrm (ai2o.online)

---

## Статус этапов

| Этап | Задача | Статус |
|------|--------|--------|
| 1 | Рефактор `api/orders` через `order_service` + `GET /*/history` | ✅ done |
| 2 | API Key аутентификация (`X-API-Key`, 403) | ✅ done |
| 3 | HTTPS — nginx + Let's Encrypt для `api.ai2o.online` | ⏳ blocked (ждём DNS) |
| 4 | `POST /orders/from-source` — единая точка входа через адаптер | ✅ done |
| 5 | Рефакторинг хранилища: PostgreSQL → Integram API | ✅ done |
| 6 | Дашборд (Vue 3 + PrimeVue 4) | ✅ done — Login, Dashboard, Orders, Clients, Products |
| 7 | Импорт заказов из Excel / Google Таблицы | ✅ done — POST /import/excel + /preview |
| 8 | Товары (Products API) | ✅ done — CRUD + soft-delete |
| 9 | Уведомления клиентам (Telegram / WhatsApp) | 📋 todo |
| 10 | UDS интеграция (официальный API или webhook) | 📋 todo |
| 11 | Дозаказ: добавлять к существующему заказу | 📋 todo |
| 12 | HTTPS + CORS из env | 📋 todo |
| 13 | Пагинация client_history (сейчас загружает все заказы в память) | 📋 todo |

---

## Следующий шаг

**Этап 9 — Уведомления клиентам:**
- Telegram-уведомления при смене статуса заказа
- Интеграция с BEEBOT (Telegram бот)
- Webhook или polling статусов

**Этап 12 — HTTPS + CORS:**
- CORS_ORIGINS вынести в переменные окружения
- Let's Encrypt через certbot/traefik

---

## Принятые решения (ADR)

| ID | Решение | Статус |
|----|---------|--------|
| ADR-001 | FastAPI + Integram API как хранилище (PostgreSQL убран) | accepted |
| ADR-002 | X-API-Key аутентификация | accepted |
| ADR-003 | Integram workspace `beecrm` — Клиенты/Заказы/История | accepted |
| ADR-004 | Soft-delete для товаров (active=False) вместо физического удаления | accepted |
| ADR-005 | Dashboard — отдельный SPA (Vue 3), API-ключ в localStorage | accepted |
| ADR-006 | Import fallback: сначала Integram import API, потом openpyxl построчно | accepted |

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
