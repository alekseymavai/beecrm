# BEECRM — План работы команды

> Ведётся командой AgentForge. Обновлять после каждого этапа.
> Решения и уроки также сохраняются в Integram (workspace: devteam).

---

## Статус этапов

| Этап | Задача | Статус |
|------|--------|--------|
| 1 | Рефактор `api/orders` через `order_service` + `GET /*/history` | ✅ done |
| 2 | API Key аутентификация (`X-API-Key`, 403) | ✅ done |
| 3 | HTTPS — nginx + Let's Encrypt для `api.ai2o.online` | ⏳ blocked (ждём DNS) |
| 4 | `POST /orders/from-source` — единая точка входа через адаптер | ✅ done |
| 5 | Импорт заказов из Excel / Google Таблицы | 📋 todo |
| 6 | Уведомления клиентам (Telegram / WhatsApp) | 📋 todo |

---

## Следующий шаг

**Этап 5 — Импорт из Excel:**
- `POST /import/excel` — принимает `.xlsx` файл
- Каждая строка → `TableAdapter.from_xlsx_row()` → `find_or_create()` → `create_order()`
- Возвращает отчёт: создано / пропущено / ошибки

---

## Принятые решения (ADR)

| ID | Решение | Статус |
|----|---------|--------|
| ADR-001 | FastAPI + SQLAlchemy + PostgreSQL | accepted |
| ADR-002 | X-API-Key аутентификация | accepted |

Полные тексты ADR — в Integram, таблица Decisions (typeId: 16), проект BEECRM.

---

## Уроки команды

Полные уроки — в Integram, таблица Lessons (typeId: 17), проект BEECRM.

| Урок | Severity |
|------|----------|
| SQLite `:memory:` + FastAPI TestClient требует `StaticPool` | medium |
| `postgresql.ENUM(create_type=False)` в `create_table`, не `sa.Enum` | medium |
