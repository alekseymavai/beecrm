# AF Исправление маппера Integram V2 API

**Pipeline:** Scout(1) -> Architect(2) -> Security(3) -> Dev(4) -> QA(5) -> DevOps(6) -> TechWriter(7)
**Telos:** Исправить парсинг ответов Integram V2 API — сейчас `list_objects` возвращает alias-формат, а маппер ожидает `requisites`-формат. В результате все поля заказов/клиентов приходят null/default.

---

## Контекст

После миграции на workspace `usadba` (25.04.2026) обнаружено: API-эндпоинты `/orders`, `/clients`, `/products` возвращают данные с дефолтными значениями:
- `client_id: null`
- `status: "NEW"` (всегда, даже для отправленных)
- `source: "MESSENGER"` (всегда)

### Причина

Integram V2 API имеет **два формата ответа**:

**`GET /objects?typeId=24` (list)** — alias-формат, ключи = имена колонок:
```json
{
  "id": 11452,
  "name": "Заказ 527609",
  "Номер": "527609",
  "Статус заказа": "Отправлен (id:133)",
  "Источник": "ВК (id:123)",
  "Клиент": "",
  "Сумма": "0 (id:6950)",
  "Дата": "1760140800"
}
```

**`GET /objects/{id}` (single)** — requisites-формат, ключи = числовые colId:
```json
{
  "id": 11452,
  "requisites": {
    "87": "133",
    "83": "42",
    "82": "123",
    "56": "2024-06-10"
  }
}
```

Маппер (`integram/mappers.py`) ожидает `requisites`-формат:
```python
req = row.get("requisites") or {}      # ← пусто для list-ответа!
status_raw = req.get("87")             # ← None
client_raw = req.get("83")             # ← None
```

### Особенности alias-формата

1. **Ref-колонки** приходят как `"Значение (id:NNN)"` — нужен парсинг
2. **Даты** приходят как unix timestamp строка (`"1760140800"`), не ISO
3. **Пустые ref** не возвращаются в ответе (ключ отсутствует)
4. **Number с ref** — `"Сумма": "0 (id:6950)"` — число и id записи вместе

### Доказательство в коде

Метод `find_user_by_login` (client.py:176) **уже знает** об этой проблеме:
```python
# Получаем список (без requisites)
rows = await self.list_objects(self.T_USERS, page_size=200)
for row in rows:
    # Для каждого — отдельный get_object (с requisites)
    obj = await self.get_object(row["id"])
    reqs = obj.get("requisites") or {}
```
Это N+1 workaround, который для Users (мало записей) приемлем, но для Orders/Products — нет.

---

## Инструкция запуска

Передай содержимое этого файла в новую Claude Code сессию как стартовый промт.
Рабочая директория: `/home/hive/BEECRM`

---

## ШАГ 0 — Загрузка контекста

```
Прочитай:
1. /home/hive/BEECRM/CLAUDE.md
2. /home/hive/BEECRM/integram/client.py (все методы list_objects, get_object, _request)
3. /home/hive/BEECRM/integram/mappers.py (все 4 маппера)
4. /home/hive/BEECRM/api/orders.py, api/clients.py, api/products.py (как вызываются маппер)
5. /home/hive/BEECRM/tests/mocks/integram_mock.py (FakeIntegramClient)
6. /home/hive/BEECRM/docs/architecture.md (секция "Integram — маппинг")
```

---

## ШАГ 1 — Ведатель: разведка формата V2 API

**Роль:** Scout. Определить точный формат обоих ответов.

**Что сделать:**

1. **Через MCP — формат list:**
   ```
   mcp__integram__switch_workspace(slug="usadba")
   mcp__integram__list_objects(typeId=24, limit=2)  — Заказы
   mcp__integram__list_objects(typeId=21, limit=2)  — Клиенты
   mcp__integram__list_objects(typeId=23, limit=2)  — Товары
   ```

2. **Через MCP — формат single:**
   ```
   mcp__integram__get_object(objId=ID_из_list)  — для каждой таблицы
   ```
   Определить: возвращает ли get_object поле `requisites`? Или тоже alias-формат?

3. **Проверить есть ли параметр для включения requisites в list:**
   Попробовать через httpx (или curl) параметры: `?include=requisites`, `?format=raw`, `?expand=true`

4. **Зафиксировать маппинг alias → colId:**

   | Alias в ответе | colId | Тип | Формат значения |
   |----------------|-------|-----|-----------------|
   | Статус заказа | 87 | ref | "Отправлен (id:133)" |
   | Источник | 82 | ref | "ВК (id:123)" |
   | Клиент | 83 | ref | "Имя (id:42)" или пусто |
   | Сумма | 60 | number(ref?) | "0 (id:6950)" |
   | Дата | 56 | date | "1760140800" (unix) |

**Формат подарка Scout -> Architect:**
```
SCOUT GIFT:
  list_format: alias / requisites / mixed
  single_format: alias / requisites / mixed
  ref_value_pattern: "Name (id:NNN)" — regex: r'\(id:(\d+)\)'
  date_format: unix_timestamp / iso8601
  include_param_exists: true/false
  empty_refs_behavior: key_absent / empty_string / null
  affected_endpoints: [/orders, /clients, /products, /orders/{id}/history]
  affected_mappers: [igm_to_order, igm_to_client, igm_to_product, igm_to_event]
```

---

## ШАГ 2 — Зодчий: план исправления

**Роль:** Architect. Два варианта.

**Вариант A — Dual-format маппер:**
- Маппер определяет формат по наличию ключа `requisites`
- Если есть `requisites` → текущая логика (числовые colId)
- Если нет → парсит alias-ключи, извлекает id из `"Name (id:NNN)"`
- Нужен маппинг alias → colId или alias → поле домена
- Плюсы: один HTTP-запрос для list, обратная совместимость
- Минусы: хрупкость парсинга `(id:NNN)`, дублирование логики

**Вариант B — Обогащение в client.py:**
- `list_objects` после получения списка вызывает `get_object` для каждого
- Или: `list_objects` конвертирует alias-формат в `requisites`-формат перед возвратом
- Плюсы: маппер не меняется, единый формат
- Минусы: N+1 запросов (медленно для 50+ записей)

**Вариант C — Переход на alias-формат полностью:**
- Маппер переписывается на alias-ключи вместо числовых colId
- `COL_ORDER_STATUS = 87` → `COL_ORDER_STATUS_ALIAS = "Статус заказа"`
- Плюсы: простой код, не зависит от внутренних ID
- Минусы: alias может меняться при переименовании колонки

**СТОП:** Подать варианты Алексею. Ждать выбора.

---

## ШАГ 3 — Блюститель: аудит плана

**Роль:** Security (1.3x, блокирующий).

**Что проверить:**
1. Парсинг `(id:NNN)` — нет ли injection через имя записи содержащее `(id:XXX)`?
2. Unix timestamp → ISO конвертация — timezone-safe?
3. FakeIntegramClient — какой формат он возвращает? Тесты покрывают оба формата?
4. Нет ли эндпоинтов которые передают raw Integram данные клиенту без маппинга?

---

## ШАГ 4 — Делатель: реализация

**Роль:** BackendDev. Код строго по плану Зодчего.

**Порядок (зависит от выбранного варианта):**

### Если Вариант A (dual-format):

1. **Хелпер парсинга ref-значений:**
   ```python
   # integram/mappers.py
   import re
   _REF_ID_RE = re.compile(r'\(id:(\d+)\)')

   def _parse_ref_id(value: str | None) -> int | None:
       """Извлечь ID из 'Название (id:123)' → 123"""
       if not value:
           return None
       m = _REF_ID_RE.search(str(value))
       return int(m.group(1)) if m else None
   ```

2. **Маппинг alias → colId (или напрямую в поле домена):**
   ```python
   # integram/client.py — добавить alias-маппинг
   ALIAS_MAP_ORDER = {
       "Статус заказа": COL_ORDER_STATUS,
       "Источник": COL_ORDER_SOURCE,
       "Клиент": COL_ORDER_CLIENT,
       "Дата": COL_ORDER_CREATED_AT,
       "Сумма": COL_ORDER_AMOUNT,
   }
   ```

3. **Обновить маппер:**
   ```python
   def igm_to_order(row: dict) -> dict:
       req = row.get("requisites")
       if req is not None:
           # requisites-формат (get_object, create_object, FakeIntegramClient)
           ...текущая логика...
       else:
           # alias-формат (list_objects V2 API)
           ...новая логика с _parse_ref_id()...
   ```

4. **Обновить FakeIntegramClient** — убедиться что тесты проходят (mock возвращает requisites-формат).

5. **Добавить тесты для alias-формата.**

### Если Вариант B (обогащение):

1. **Обновить `list_objects` в client.py:**
   ```python
   async def list_objects(self, typeId, ...):
       data = await self._request(...)
       rows = ...
       # Обогащение: для каждого row без requisites — подгрузить
       enriched = []
       for r in rows:
           if "requisites" not in r:
               full = await self.get_object(r["id"])
               enriched.append(full or r)
           else:
               enriched.append(r)
       return enriched
   ```

2. **Маппер не меняется.**

---

## ШАГ 5 — Испытатель: тесты

**Роль:** QA (1.2x).

```bash
python3 -m pytest tests/ -v
```

**Дополнительно:**
1. Тест с реальным alias-форматом (unit test с fixture):
   ```python
   def test_igm_to_order_alias_format():
       row = {
           "id": 11452,
           "name": "Заказ 527609",
           "Статус заказа": "Отправлен (id:133)",
           "Источник": "ВК (id:123)",
           "Клиент": "Иванов (id:42)",
           "Дата": "1760140800",
       }
       result = igm_to_order(row)
       assert result["status"] == "DONE"  # 133 → mapped
       assert result["client_id"] == 42
   ```

2. Smoke test на проде:
   ```bash
   curl -s -H "X-API-Key: $API_KEY" https://usadbadmitrov.ru/api/orders?limit=2 | jq '.[0] | {client_id, status, source}'
   ```

---

## ШАГ 6 — Устроитель: деплой

**Роль:** DevOps.

```bash
gh auth switch -u alekseymavai && gh auth setup-git
git push origin main
ssh ai-agent@178.253.39.215 "cd ~/BEECRM && git pull && sudo systemctl restart beecrm"
```

Smoke test после деплоя.

---

## ШАГ 7 — Летописец: документация

**Роль:** TechWriter.

1. **docs/architecture.md** — добавить секцию "Форматы ответа Integram V2 API"
2. **docs/plan.md** — ADR для выбранного варианта
3. **MEMORY.md** — запись о формате V2 API

---

## ИТОГ — Consensus Report

```markdown
# AF Fix V2 Mappers — Consensus Report

**Security status:** [GREEN/YELLOW/RED]
**Дата:** [дата]

## Проблема
list_objects возвращает alias-формат без requisites. Маппер ожидает requisites → все поля null.

## Решение
[Выбранный вариант A/B/C]

## Изменения
| Файл | Что изменилось |
|------|---------------|
| integram/mappers.py | ... |
| integram/client.py | ... |
| tests/test_mappers.py | ... |

## Тесты
- Всего: ?
- Зелёных: ?

## Smoke test
- /orders — client_id, status, source корректны: YES/NO
- /clients — phone, email корректны: YES/NO
- /products — price, category корректны: YES/NO

human_decision_required: true
```

Сохрани отчет в `docs/agentforge/report_fix_v2_mappers_{YYYYMMDD}.md`
