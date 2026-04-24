# AF Миграция на workspace usadba — Полный цикл

**Pipeline:** Security(0) -> Scout(1) -> Architect(2) -> Security(3) -> Dev(4) -> QA(5) -> DevOps(6) -> TechWriter(7) -> Phase_H(8)
**Telos:** Перевести BEECRM с workspace `beecrm` (тестовый) на `usadba` (продакшн) без потери функциональности

---

## Контекст

Проект BEECRM работает на Integram workspace `beecrm` (ai2o.online/beecrm).
Есть более актуальный workspace `usadba` (ai2o.online/usadba) с реальными данными.
Решение: полная миграция на `usadba`.

### Ключевые факты

**usadba** — зрелая схема:
- 9 реальных клиентов, 9 заказов, 9 товаров
- Расширенная схема: UDS ID, Баллы, Сумма покупок, Уровни лояльности, Адреса (child), Дозаказы (child), Комментарии (child)
- Справочники заполнены: 8 источников, 6 статусов заказа, 4 статуса оплаты, 3 уровня лояльности

**beecrm** — тестовый:
- 5 клиентов `[TEST]`, 4 заказа `[TEST]`
- Менее полная схема, но есть таблицы, которых нет в usadba

**Проблема:** ВСЕ typeId и colId другие. Код жёстко привязан к beecrm.

### Чего нет в usadba (нужно досоздать)

| Таблица | В beecrm | В usadba | Нужна? |
|---------|----------|----------|--------|
| Пользователи CRM | typeId=1578 (4 колонки: login, hash, role, active) | нет | ДА — JWT auth |
| История изменений заказа | typeId=22 (child of 20, 5 колонок) | нет | ДА — event tracking |
| Статусы коммуникации | typeId=1534 (5 значений) | нет | РЕШИТЬ |
| Источник (дубль) | typeId=1590 (пустая) | нет | НЕТ — мусор |

### Маппинг typeId: beecrm -> usadba

| Таблица | beecrm | usadba |
|---------|--------|--------|
| Статусы заказов | 14 | 15 |
| Источники | 15 | 14 |
| Способы доставки | 16 | 19 |
| Категории товаров | 17 | 17 |
| Товары | 18 | 23 |
| Клиенты | 19 | 21 |
| Заказы | 20 | 24 |
| Позиции заказа | 21 (child of 20) | 25 (child of 24, "Товары заказа") |
| История изменений | 22 (child of 20) | НЕТ — создать |
| Мессенджеры | 1532 | 18 |
| Статусы оплаты | 1533 | 16 |
| Статусы коммуникации | 1534 | НЕТ — решить |
| Пользователи CRM | 1578 | НЕТ — создать |
| Уровни лояльности | нет | 20 |
| Адреса (child Клиенты) | нет | 22 |
| Дозаказы (child Заказы) | нет | 26 |
| Комментарии (child Заказы) | нет | 27 |

### Маппинг STATUS_MAP (record IDs)

| Статус | beecrm ID | usadba ID |
|--------|-----------|-----------|
| Новый | 61 | 130 |
| Подтверждён / В обработке | 62 | 131 |
| В сборке / Собран | 63 | 132 |
| Отправлен | 64 | 133 |
| Доставлен | 65 | 134 |
| Отменён | 66 | 135 |
| Завершен | 67 | нет |

### Маппинг SOURCE_MAP (record IDs)

| Источник | beecrm ID | usadba ID |
|----------|-----------|-----------|
| ВК | 68 | 123 |
| Instagram | 69 | 124 |
| Telegram | 70 | 125 |
| WhatsApp | 71 | 126 |
| UDS | 72 | 122 |
| Личное обращение | 73 | 128 |
| Сообщество | 74 | нет |
| Мессенджер | нет | 127 |
| Портал | нет | 129 |

### Маппинг colId: Клиенты (beecrm 19 -> usadba 21)

| Колонка | beecrm colId | usadba colId |
|---------|-------------|-------------|
| Телефон | 32 | 29 |
| Email | 1588 | 30 |
| Telegram ID | 33 | 32 |
| Telegram Username | 34 | 33 |
| Комментарий/Примечание | 37 | 39 |
| Мессенджер | 1550 | 78 |
| UDS ID | нет | 31 |
| Баллы | нет | 34 |
| Сумма покупок | нет | 35 |
| Кол-во заказов | нет | 36 |
| Дата регистрации | нет | 37 |
| Дата последнего заказа | нет | 38 |
| Источник | нет | 79 |
| Уровень лояльности | нет | 80 |
| Адрес | 35 | нет (child-таблица 22) |
| Город | 36 | нет (child-таблица 22) |

### Маппинг colId: Заказы (beecrm 20 -> usadba 24)

| Колонка | beecrm colId | usadba colId |
|---------|-------------|-------------|
| Номер | 38 | 55 |
| Дата | 39 | 56 |
| Адрес доставки | 40 | 59 |
| Трек-номер | 41 | 64 |
| Сумма товаров | 42 | нет (единая Сумма=60) |
| Стоимость доставки | 43 | нет |
| Итого | 44 | нет (Сумма=60 валюта) |
| Комментарий | 45 | нет (child-таблица 27) |
| Клиент | 57 | 83 |
| Статус | 58 | нет в schema (Статус заказа) |
| Способ доставки | 59 | 85 |
| Дата отправки | 1549 | 62 |
| Вес (кг) | 1552 | 66 |
| Длина (см) | 1553 | 67 |
| Ширина (см) | 1554 | 68 |
| Высота (см) | 1555 | 69 |
| Статус оплаты | 1556 | 86 |
| Источник | 1589 | 82 |
| ФИО получателя | нет | 57 |
| Телефон получателя | нет | 58 |
| Проведён в UDS | нет | 61 |
| Ожидаемая дата доставки | нет | 63 |
| ПВЗ факт | нет | 65 |
| Мессенджер для трека | нет | 84 |

---

## Инструкция запуска

Передай содержимое этого файла в новую Claude Code сессию как стартовый промт.
Рабочая директория: `/home/hive/BEECRM`

---

## ШАГ 0 — Загрузка контекста

```
Прочитай:
1. /home/hive/BEECRM/CLAUDE.md
2. /home/hive/BEECRM/docs/architecture.md (маппинг beecrm — секция "Integram")
3. /home/hive/BEECRM/integram/client.py (все константы typeId/colId)
4. /home/hive/BEECRM/integram/mappers.py (маппинг полей)
5. /home/hive/BEECRM/settings.py (INTEGRAM_WORKSPACE)
6. /home/hive/BEECRM/.env (текущий workspace)
```

Подтверди что прочитал и понял: текущий workspace `beecrm`, целевой `usadba`.

---

## ШАГ 1 — Блюститель: безопасность (немедленно)

**Роль:** Security. Устранить утечки ПД до любых других действий.
**Блокирует:** весь дальнейший pipeline пока не выполнено.

**Что сделать:**

1. **Обновить .gitignore:**
   ```
   # Добавить:
   .playwright-mcp/
   dashboard/node_modules/
   .claude/
   ```

2. **Удалить .playwright-mcp/ целиком:**
   ```bash
   rm -rf .playwright-mcp/
   ```
   Содержит 8 CSV с персональными данными клиентов (ФИО, телефоны, адреса доставки) + скриншоты + логи.

3. **Проверить что .env не в git:**
   ```bash
   git ls-files -- .env
   ```

4. **Коммит:**
   ```
   fix(security): add .playwright-mcp and node_modules to .gitignore, remove PD files
   ```

**СТОП:** Подтверди у Алексея что .playwright-mcp/ можно удалить безвозвратно.

---

## ШАГ 2 — Ведатель: разведка usadba

**Роль:** Scout. Проверить актуальное состояние usadba через MCP.

**Что сделать:**

1. **Переключиться на usadba:**
   ```
   mcp__integram__switch_workspace(slug="usadba")
   ```

2. **Получить полные схемы всех таблиц:**
   ```
   list_tables()
   get_table_schema(typeId) — для каждой таблицы
   ```

3. **Проверить данные:**
   ```
   list_objects(typeId=21, limit=5)  — Клиенты
   list_objects(typeId=24, limit=5)  — Заказы
   list_objects(typeId=23, limit=5)  — Товары
   list_objects(typeId=25, limit=5)  — Товары заказа
   ```

4. **Проверить colId для Заказы.Статус заказа:**
   В schema typeId=24 колонка "Статус заказа" не была видна в предыдущей разведке.
   Проверить через get_table_schema(24) — найти точный colId.

5. **Сверить маппинг из этого документа с реальностью.**
   Если есть расхождения — зафиксировать.

**Формат подарка Scout -> Architect:**
```
SCOUT GIFT:
  usadba_verified: true/false
  schema_mismatches: [список расхождений с документом выше]
  missing_tables: [что нужно досоздать]
  missing_columns: [колонки которых нет но нужны коду]
  data_counts: {clients: N, orders: N, products: N}
  colId_corrections: {описание -> правильный colId}
```

---

## ШАГ 3 — Зодчий: план миграции

**Роль:** Architect. Два варианта плана.

**Задача:** На основе SCOUT GIFT спроектировать миграцию.

**Обязательные решения:**

1. **Досоздать в usadba через MCP:**
   - Таблица "Пользователи CRM" (4 колонки: login text, password_hash text, role text, is_active bool)
   - Таблица "История изменений заказа" (child of Заказы=24, колонки: Предыдущий статус, Новый статус, Кто изменил, Описание, Дата)
   - Решение по "Статусы коммуникации" — создавать в usadba или убрать из кода?

2. **Стратегия ремаппинга кода:**

   **Вариант A — Прямая замена констант:**
   - Заменить все typeId/colId в `integram/client.py`
   - Обновить STATUS_MAP, SOURCE_MAP
   - Обновить mappers.py
   - Плюсы: быстро, просто
   - Минусы: хардкод остаётся, следующая миграция — та же боль

   **Вариант B — Конфиг-файл маппинга:**
   - Вынести typeId/colId в `integram/schema.py` или YAML
   - client.py читает из конфига
   - Плюсы: следующая миграция = замена конфига
   - Минусы: больше работы сейчас, overhead для одного workspace

3. **Что делать с полями, которых нет в usadba:**
   - Заказы: `Сумма товаров` + `Стоимость доставки` + `Итого` (3 поля) -> usadba имеет только `Сумма` (валюта). Как маппить?
   - Заказы: `Комментарий` (memo) -> usadba: child-таблица `Комментарии`. Как маппить?
   - Клиенты: `Адрес` + `Город` -> usadba: child-таблица `Адреса`. Как маппить?

4. **Что делать с новыми полями usadba, которых нет в коде:**
   - Клиенты: UDS ID, Баллы, Сумма покупок, Уровень лояльности — игнорировать или добавить поддержку?
   - Заказы: ФИО получателя, Телефон получателя, Проведён в UDS — добавить в маппер?

**СТОП:** Подать план A и B Алексею. Ждать выбора.

---

## ШАГ 4 — Блюститель: аудит плана

**Роль:** Security (1.3x, блокирующий).

**Что проверить:**
1. Токен/логин Integram — одинаковый для beecrm и usadba? Или нужен отдельный?
2. .env на VPS (178.253.39.215) — нужно обновить INTEGRAM_WORKSPACE?
3. Пользователи CRM в usadba — хеши паролей не должны попасть в логи
4. Нет ли в коде хардкода `beecrm` кроме settings.py и .env?

```bash
grep -rn "beecrm" --include="*.py" --include="*.env" --include="*.yaml" .
```

**DECLINED если:**
- Токен Integram расшарен между workspace'ами без изоляции
- Хардкод `beecrm` остаётся в продакшн-коде после миграции

---

## ШАГ 5 — Делатель: реализация

**Роль:** BackendDev. Код строго по плану Зодчего.

**Порядок:**

### 5a — Досоздать таблицы в usadba (MCP)

```
mcp__integram__switch_workspace(slug="usadba")
# Активировать schema tools:
search_tools("schema")

# 1. Пользователи CRM
create_table(name="Пользователи CRM")
add_column(typeId=NEW_ID, alias="login", colTypeName="text")
add_column(typeId=NEW_ID, alias="password_hash", colTypeName="text")
add_column(typeId=NEW_ID, alias="role", colTypeName="text")
add_column(typeId=NEW_ID, alias="is_active", colTypeName="bool")

# 2. История изменений заказа (child of Заказы=24)
create_table(name="История изменений заказа", parentTypeId=24)
add_column(typeId=NEW_ID, alias="Предыдущий статус", colTypeName="text")
add_column(typeId=NEW_ID, alias="Новый статус", colTypeName="text")
add_column(typeId=NEW_ID, alias="Кто изменил", colTypeName="text")
add_column(typeId=NEW_ID, alias="Описание", colTypeName="memo")
add_column(typeId=NEW_ID, alias="Дата изменения", colTypeName="datetime")
```

**Записать новые typeId и colId!**

### 5b — Ремаппинг integram/client.py

Заменить все константы по выбранному варианту (A или B).
Ключевые блоки:
- `T_CLIENTS`, `T_ORDERS`, `T_PRODUCTS`, `T_EVENTS`, `T_STATUSES`, `T_SOURCES`
- `T_USERS`, `COL_USER_*`
- `COL_PRODUCT_*`
- `COL_CLIENT_*`
- `COL_ORDER_*`
- `COL_EVENT_*`
- `STATUS_MAP`, `SOURCE_MAP`
- Дефолтный workspace в `__init__` и `authenticate`: `"beecrm"` -> `"usadba"`

### 5c — Ремаппинг mappers

Файл `integram/mappers.py` — обновить все colId в маппинге полей.

### 5d — Обновить settings.py и .env

```python
# settings.py
INTEGRAM_WORKSPACE: str = "usadba"
# ...
INTEGRAM_WORKSPACE = os.environ.get("INTEGRAM_WORKSPACE", "usadba")
```

```env
# .env
INTEGRAM_WORKSPACE=usadba
```

### 5e — Обновить apiary/config.py

```python
INTEGRAM_WORKSPACE: str = os.environ.get("INTEGRAM_WORKSPACE", "usadba")
```

### 5f — Проверить все остальные файлы с хардкодом "beecrm"

```bash
grep -rn "beecrm" --include="*.py" .
# Каждое вхождение — заменить или убрать
```

---

## ШАГ 6 — Испытатель: тесты

**Роль:** QA (1.2x). Запустить все тесты.

```bash
cd /home/hive/BEECRM
python -m pytest tests/ -v
```

**Что проверить:**
1. Все существующие тесты проходят (FakeIntegramClient — не зависит от реального workspace)
2. Если тесты хардкодят beecrm typeId/colId — обновить
3. STATUS_MAP и SOURCE_MAP — новые ID в тестах

**DEFER если:** красные тесты -> возврат Делателю с описанием.

---

## ШАГ 7 — Устроитель: деплой

**Роль:** DevOps. Только после зелёного Испытателя.

**Что сделать:**

1. **Коммит:**
   ```bash
   git add -A
   git commit -m "feat(integram): migrate from workspace beecrm to usadba

   - Remap all typeId/colId constants in client.py
   - Update STATUS_MAP, SOURCE_MAP with usadba record IDs
   - Update mappers for new column structure
   - Create Пользователи CRM and История tables in usadba
   - Update default workspace in settings.py and .env

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
   ```

2. **Push:**
   ```bash
   gh auth switch -u alekseymavai && gh auth setup-git
   git push origin main
   ```

3. **Деплой на VPS:**
   ```bash
   ssh ai-agent@178.253.39.215 "cd ~/BEECRM && git pull"
   ```

4. **Обновить .env на VPS:**
   ```bash
   ssh ai-agent@178.253.39.215 "cd ~/BEECRM && sed -i 's/INTEGRAM_WORKSPACE=beecrm/INTEGRAM_WORKSPACE=usadba/' .env"
   ```

5. **Рестарт:**
   ```bash
   ssh ai-agent@178.253.39.215 "sudo systemctl restart beecrm"
   ```

6. **Smoke test:**
   ```bash
   curl -s https://usadbadmitrov.ru/api/health | jq .
   curl -s -H "X-API-Key: $API_KEY" https://usadbadmitrov.ru/api/orders?limit=2 | jq .
   ```

---

## ШАГ 8 — Летописец: документация

**Роль:** TechWriter. Обновить всё что ссылается на beecrm.

**Что сделать:**

1. **docs/architecture.md:**
   - Секция "Integram — маппинг" — полная перезапись на usadba typeId/colId
   - Диаграмма: `ai2o.online/beecrm` -> `ai2o.online/usadba`
   - Журнал изменений: добавить запись о миграции

2. **docs/plan.md:**
   - Строка 4: `beecrm` -> `usadba`
   - ADR-003: обновить
   - Добавить ADR для миграции

3. **CLAUDE.md:**
   - Проверить нет ли ссылок на beecrm

4. **README.md:**
   - Обновить если упоминает workspace

5. **Обновить MEMORY.md** (claude projects memory):
   - Добавить запись о миграции на usadba

---

## ШАГ 9 — Phase_H: Cleanup (отдельный подцикл)

После успешной миграции — запустить `/home/hive/BEECRM/docs/agentforge/phase_H.md`.
К этому моменту phase_H будет работать на актуальной кодовой базе.

Дополнительно к phase_H — удалить мёртвый код:
- `scripts/dedup_products.py` — хардкодит `beecrm` URL
- `scripts/reimport_products.py` — хардкодит `beecrm` URL
- `scripts/import_uds_april.py` — хардкодит `beecrmtest`
- Таблица-дубль "Источник" (typeId=1590) в beecrm — уже не актуальна

---

## ИТОГ — Consensus Report

```markdown
# AF Migration usadba — Consensus Report

**Security status:** [GREEN/YELLOW/RED]
**Дата:** [дата]

## Безопасность (Блюститель)
- [ ] .playwright-mcp/ удалён (ПД клиентов)
- [ ] .gitignore обновлён
- [ ] Хардкод beecrm удалён из prod-кода
- [ ] .env на VPS обновлён

## Досозданные таблицы в usadba
| Таблица | typeId | Колонки | Статус |
|---------|--------|---------|--------|
| Пользователи CRM | ? | login, hash, role, active | ? |
| История изменений заказа | ? | from, to, actor, meta, time | ? |

## Ремаппинг (Делатель)
| Файл | Изменения | Статус |
|------|-----------|--------|
| integram/client.py | typeId, colId, STATUS_MAP, SOURCE_MAP | ? |
| integram/mappers.py | colId маппинг | ? |
| settings.py | default workspace | ? |
| .env | INTEGRAM_WORKSPACE | ? |
| apiary/config.py | default workspace | ? |

## Тесты (Испытатель)
- Всего: ?
- Зелёных: ?
- Красных: ?

## Деплой (Устроитель)
- [ ] Push to GitHub
- [ ] git pull на VPS
- [ ] .env обновлён на VPS
- [ ] systemctl restart
- [ ] Smoke test passed

## Документация (Летописец)
- [ ] docs/architecture.md — маппинг usadba
- [ ] docs/plan.md — workspace updated
- [ ] MEMORY.md — запись о миграции

## Рекомендация
[итог + следующий шаг: Phase_H cleanup]

human_decision_required: true
```

Сохрани отчёт в `docs/agentforge/report_migration_usadba_{YYYYMMDD}.md`
