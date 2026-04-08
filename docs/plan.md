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
| 6 | Дашборд (Vue 3 + PrimeVue 4) | 📋 todo |
| 7 | Импорт заказов из Excel / Google Таблицы | 📋 todo |
| 8 | Уведомления клиентам (Telegram / WhatsApp) | 📋 todo |

---

## Следующий шаг

**Этап 6 — Дашборд (Vue 3 + PrimeVue 4):**
- Папка `web/` в репозитории BEECRM
- Подключается к BEECRM API через X-API-Key
- Страницы: Заказы, Клиенты, Статистика
- Skeleton UI + Pinia кэш для быстрой загрузки

---

## Принятые решения (ADR)

| ID | Решение | Статус |
|----|---------|--------|
| ADR-001 | FastAPI + Integram API как хранилище (PostgreSQL убран) | accepted |
| ADR-002 | X-API-Key аутентификация | accepted |
| ADR-003 | Integram workspace `beecrm` — Клиенты/Заказы/История | accepted |

---

## Уроки команды

| Урок | Severity |
|------|----------|
| SQLite `:memory:` + FastAPI TestClient требует `StaticPool` | medium |
| `postgresql.ENUM(create_type=False)` в `create_table`, не `sa.Enum` | medium |
| FakeIntegramClient (in-memory dict) — правильный подход для тестов без реального Integram | medium |
| Integram не поддерживает ACID: event создаётся до обновления статуса (compensating actions) | high |
