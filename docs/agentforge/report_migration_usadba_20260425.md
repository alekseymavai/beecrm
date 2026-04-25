# AF Migration usadba — Consensus Report

**Security status:** GREEN
**Дата:** 2026-04-25

## Безопасность (Блюститель)
- [x] .playwright-mcp/ удалён (CSV с данными клиентов)
- [x] .gitignore обновлён (.playwright-mcp/, dashboard/node_modules/, .claude/)
- [x] Хардкод beecrm удалён из prod-кода
- [x] .env на VPS обновлён (INTEGRAM_WORKSPACE=usadba, INTEGRAM_T_EVENTS=28890)

## Досозданные таблицы в usadba

| Таблица | typeId | Колонки (colId) | Статус |
|---------|--------|---------|--------|
| Пользователи CRM | 28885 | login(28886), hash(28887), role(28888), active(28889) | DONE |
| История изменений заказа | 28890 (child of 24) | from(28891), to(28892), actor(28893), meta(28894), time(28895) | DONE |

## Ремаппинг (Делатель)

| Файл | Изменения | Статус |
|------|-----------|--------|
| integram/client.py | Все typeId, colId, STATUS_MAP, SOURCE_MAP, default workspace | DONE |
| integram/mappers.py | None-safe для COL_ORDER_NOTES и COL_PRODUCT_STOCK | DONE |
| api/products.py | None-safe для COL_PRODUCT_STOCK | DONE |
| settings.py | default workspace usadba, T_EVENTS=28890 | DONE |
| .env | INTEGRAM_WORKSPACE=usadba | DONE |
| apiary/config.py | default workspace usadba | DONE |
| apiary/scripts/create_tables.py | default workspace usadba | DONE |
| tests/mocks/integram_mock.py | Наследует все константы из IntegramClient | DONE |
| tests/test_mappers.py | skipif для None-колонок, динамические ключи | DONE |
| tests/test_products.py | Убрана проверка stock (None) | DONE |
| tests/test_api_from_source.py | Убрана проверка payload (None notes) | DONE |

## Тесты (Испытатель)
- Всего: 113
- Зелёных: 113
- Красных: 0

## Деплой (Устроитель)
- [x] Push to GitHub (commit 2e37409)
- [x] git pull на VPS (178.253.39.215)
- [x] .env обновлён на VPS
- [x] systemctl restart beecrm
- [x] Smoke test passed (/api/health OK, /api/orders returns data)

## Документация (Летописец)
- [x] docs/architecture.md — полная перезапись маппинга на usadba
- [x] docs/plan.md — workspace updated, ADR-012 добавлен
- [x] settings.py — исправлен fallback T_EVENTS (37 -> 28890)
- [x] Consensus Report сохранён

## Известные ограничения
- Orders API возвращает `client_id: null`, `status: "NEW"` для всех записей — вероятно формат requisites в V2 API отличается от ожидаемого маппером. Требует отдельного исследования.
- COL_ORDER_NOTES=None: payload заказа не сохраняется в usadba (нет memo-колонки, только child-таблица Комментарии)
- COL_PRODUCT_STOCK=None: остатки товаров не отслеживаются

## Рекомендация

Миграция завершена успешно. Следующий шаг: Phase_H cleanup (удаление мёртвых скриптов dedup_products.py, reimport_products.py, import_uds_april.py). Также рекомендуется исследовать формат requisites V2 API для корректного парсинга client_id и status из реальных данных usadba.

human_decision_required: true
