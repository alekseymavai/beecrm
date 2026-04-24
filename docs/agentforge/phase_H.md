# AF Фаза H — Repo Hygiene: Инвентаризация и наведение порядка

**Pipeline:** Scout -> Architect -> DevOps -> TechWriter
**Telos:** Очистить репозиторий BEECRM от накопившегося мусора, выстроить структуру и правила чтобы бардак не вернулся

---

## Контекст проблемы

Репозиторий BEECRM вырос за десятки итераций (auth, импорт UDS, дашборд, beelog-миграция, AgentForge спринты).
Накопилось:
- **135 файлов в `.playwright-mcp/`** (6.9 МБ) — логи, скриншоты, CSV-выгрузки заказов, не в .gitignore
- **8 CSV с заказами** — в `.playwright-mcp/`, содержат персональные данные клиентов (ФИО, телефоны, адреса)
- **12 директорий `__pycache__/`** — на диске, но в .gitignore (проверить что не в git)
- **`dashboard/node_modules/`** (107 МБ) — не в git, но и не в .gitignore
- **`docs/superpowers/`** — директория от Claude Superpowers (один план auth-register), нужна ли?
- **`docs/feature_get_current_user.md`** — одноразовый feature-doc (коммит 65798cc), завершённый
- **Loose файлы в корне** — `main.py`, `settings.py` (рабочие), `README.md`, `CLAUDE.md`
- **3 скрипта в `scripts/`** — `dedup_products.py`, `reimport_products.py`, `import_uds_april.py` (одноразовые?)

Цель: привести репо в состояние где новый разработчик за 10 минут поймёт что где лежит. Убрать персональные данные из untracked файлов.

---

## Инструкция запуска

Передай содержимое этого файла в новую Claude Code сессию как стартовый промт.

---

## ШАГ 0 — Загрузка контекста

```
Прочитай:
1. /home/hive/BEECRM/CLAUDE.md
2. /home/hive/BEECRM/docs/architecture.md
3. /home/hive/BEECRM/docs/plan.md
4. /home/hive/.claude/projects/-home-hive-BEECRM/memory/MEMORY.md
```

Подтверди: текущую архитектуру (FastAPI + Integram), модули (api/, integram/, services/, adapters/, uds/, apiary/, dashboard/).

---

## ШАГ 1 — Шляпа SCOUT

**Роль:** Разведчик. Инвентаризация всего что есть — без оценок, только факты.
**Профессиональная слепота:** не делаю выводов, только фиксирую.

**Задача:** Полная карта содержимого репозитория с классификацией: живое / мертвое / неясно.

**Что сделать:**

1. **`.playwright-mcp/` (135 файлов, 6.9 МБ):**
   ```bash
   ls -la .playwright-mcp/
   # Классификация:
   # - *.csv — выгрузки заказов с ПД клиентов (ФИО, телефоны, адреса)
   # - *.png — скриншоты сессий
   # - *.yml — page snapshots
   # - *.log — console logs
   # Нужны ли какие-то из них? Или всё в .gitignore + удалить?
   ```

2. **`.gitignore` — текущие пробелы:**
   ```bash
   cat .gitignore
   # Отсутствуют:
   # - .playwright-mcp/
   # - dashboard/node_modules/
   # - .claude/
   # Проверить что __pycache__/ и .pytest_cache/ реально не в git
   git ls-files -- '*/__pycache__/*' '*.pyc' '.pytest_cache/' | head -10
   ```

3. **Docs (4 файла):**
   ```bash
   find docs/ -name "*.md" -exec ls -la {} \;
   # architecture.md — актуален (обновлён 18.04.2026)
   # plan.md — актуален (план работы)
   # feature_get_current_user.md — одноразовый, завершён (коммит 65798cc)
   # docs/superpowers/plans/2026-04-15-auth-register.md — Claude Superpowers артефакт
   # Ссылаются ли из CLAUDE.md или architecture.md?
   grep -r "feature_get_current_user\|superpowers" CLAUDE.md docs/architecture.md docs/plan.md
   ```

4. **Scripts (3 штуки):**
   ```bash
   ls -la scripts/*.py
   # dedup_products.py — одноразовый скрипт дедупликации товаров
   # reimport_products.py — одноразовый реимпорт
   # import_uds_april.py — одноразовый импорт апрельских данных
   # Для каждого: git log -1 --format='%ai %s' -- scripts/FILE
   # Импортируется ли из другого кода?
   grep -r "scripts/" api/ services/ integram/ main.py --include="*.py"
   ```

5. **Top-level файлы:**
   ```bash
   ls -la *.md *.py *.sh 2>/dev/null
   # main.py — точка входа FastAPI (рабочий)
   # settings.py — конфигурация (рабочий)
   # README.md — документация проекта
   # CLAUDE.md — контекст для Claude Code
   ```

6. **Dashboard:**
   ```bash
   ls dashboard/
   du -sh dashboard/node_modules/ dashboard/dist/
   cat dashboard/.gitignore 2>/dev/null
   # node_modules/ — 107 МБ, не в git, но не в .gitignore корня
   # dist/ — есть ли в git? Нужен ли?
   git ls-files -- dashboard/dist/ | head -5
   ```

7. **Untracked файлы:**
   ```bash
   git status -s
   # Что из этого нужно закоммитить?
   # Что нужно в .gitignore?
   ```

**Формат подарка Scout -> Architect:**
```
SCOUT GIFT:

playwright_mcp:
  total_files: 135
  size: 6.9 МБ
  csv_with_personal_data: [список CSV с ПД клиентов]
  screenshots: [количество]
  logs: [количество]
  verdict: "gitignore + delete all / keep CSV / ..."

gitignore_gaps:
  missing: [.playwright-mcp/, dashboard/node_modules/, .claude/, ...]
  already_covered: [__pycache__/, .env, .pytest_cache/, ...]
  in_git_but_shouldnt_be: [список если есть]

docs_inventory:
  current: [актуальные, ссылаются из CLAUDE.md/plan.md]
  stale: [устаревшие одноразовые]
  superpowers_artifacts: [Claude Superpowers файлы]

scripts_inventory:
  active: [используются регулярно]
  one_shot: [одноразовые импорт/миграция скрипты]
  broken: [битые импорты если есть]

dashboard:
  node_modules_in_git: true/false
  dist_in_git: true/false
  has_own_gitignore: true/false

toplevel_loose_files: [с вердиктом: keep/move/delete]
untracked_files: [с вердиктом: commit/gitignore/delete]
security_concerns: [CSV с ПД, .env утечки, токены]
```

---

## ШАГ 2 — Шляпа ARCHITECT

**Роль:** Архитектор. Проектирую целевую структуру репозитория.
**Профессиональная слепота:** могу переусложнить структуру.

**Задача:** На основе SCOUT GIFT спроектировать целевую организацию репо.

**Что сделать:**

1. **Безопасность (приоритет 0):**
   - CSV с персональными данными клиентов — удалить из репо безусловно
   - Проверить что `.env` нигде не закоммичен
   - `.playwright-mcp/` — полностью в .gitignore

2. **Целевая структура `.gitignore`:**
   - Добавить: `.playwright-mcp/`, `dashboard/node_modules/`, `.claude/`
   - Проверить: `dashboard/dist/` уже есть, но правильно ли?
   - Нужен ли `dashboard/.gitignore` отдельный?

3. **Целевая структура `docs/`:**
   - `docs/architecture.md` — keep
   - `docs/plan.md` — keep
   - `docs/agentforge/` — keep (AF промты)
   - Одноразовые feature-docs и superpowers — архив или удалить?
   - Нужен ли `docs/archive/`?

4. **Целевая структура `scripts/`:**
   - Одноразовые скрипты импорта/миграции — пометить как `scripts/migrations/`? Или оставить как есть?
   - Нужен ли `scripts/README.md`?

5. **Dashboard cleanup:**
   - `node_modules/` — только в .gitignore (не в git и не должен)
   - `dist/` — в git или нет? Если деплой через `git pull` на VPS — нужен

6. **Правила на будущее:**
   - Naming conventions для скриптов
   - Что попадает в git, что в .gitignore
   - Куда складывать одноразовые feature-docs

**Формат подарка Architect -> DevOps:**
```
ARCHITECT GIFT:

security_immediate:
  delete: [файлы с ПД которые нужно удалить немедленно]
  verify: [что проверить на утечки]

gitignore_update:
  add_patterns: [новые паттерны]
  remove_patterns: [устаревшие если есть]

docs:
  keep: [список]
  archive: [список -> docs/archive/]
  delete: [список]

scripts:
  keep: [список]
  reorganize: [{file -> destination}]
  delete: [список]

dashboard:
  gitignore_changes: [что добавить]

naming_conventions: [правила для будущего]
```

---

## ШАГ 3 — Шляпа DEVOPS

**Роль:** Инженер инфраструктуры. Превращаю план Архитектора в исполняемые действия.
**Профессиональная слепота:** могу переавтоматизировать простые вещи.

**Задача:** Реализовать cleanup + защита от повторного бардака.

**Что сделать:**

1. **Cleanup plan (конкретные команды):**
   - Порядок: .gitignore -> удаление ПД -> перемещения -> архивация -> коммит
   - Каждая операция — отдельный коммит (чтобы можно было откатить)
   - НЕ ВЫПОЛНЯТЬ команды — только составить план. Исполнение — отдельная сессия Делатель.

2. **.gitignore обновление (коммит 1):**
   ```
   # Добавить в .gitignore:
   .playwright-mcp/
   dashboard/node_modules/
   .claude/
   ```

3. **Удаление ПД (коммит 2):**
   ```bash
   # Удалить CSV с персональными данными клиентов
   rm -rf .playwright-mcp/
   # Или переместить CSV в безопасное место вне репо если нужны для импорта
   ```

4. **Docs cleanup (коммит 3):**
   ```bash
   # Переместить одноразовые docs в archive/ или удалить
   mkdir -p docs/archive
   mv docs/feature_get_current_user.md docs/archive/
   mv docs/superpowers/ docs/archive/
   ```

5. **Деплой на VPS (после cleanup):**
   ```bash
   ssh ai-agent@178.253.39.215 "cd ~/BEECRM && git pull && sudo systemctl restart beecrm"
   ```

**Формат подарка DevOps -> TechWriter:**
```
DEVOPS GIFT:

cleanup_commands:
  commit_1_gitignore: [команды]
  commit_2_security_pd_cleanup: [команды]
  commit_3_docs_archive: [команды]
  commit_4_scripts_organize: [команды если нужно]

gitignore_final: [полный итоговый .gitignore]
deploy_command: "ssh ai-agent@178.253.39.215 ..."
```

---

## ШАГ 4 — Шляпа TECH WRITER

**Роль:** Технический писатель. Документирую итоговое состояние.
**Профессиональная слепота:** могу передокументировать очевидное.

**Задача:** Обновить документацию чтобы она отражала новую структуру.

**Что сделать:**

1. **CLAUDE.md — проверить ссылки:**
   - Убрать ссылки на удаленные/перемещенные файлы если есть
   - Добавить ссылку на docs/agentforge/ если уместно

2. **docs/architecture.md — обновить если нужно:**
   - Секция структуры проекта — соответствует ли реальности?
   - Убрать упоминания удаленных файлов

3. **scripts/README.md (опционально):**
   - Таблица скриптов с описанием и статусом (active/one-shot/deprecated)

4. **Проверка ссылок:**
   ```bash
   # Найти все ссылки на файлы в md-файлах и проверить что они не битые
   grep -rn '\.\./\|\./' docs/ CLAUDE.md README.md --include="*.md" | head -30
   ```

5. **Обновить MEMORY.md:**
   - Добавить запись о phase_H cleanup

---

## ИТОГ — Consensus Report

```markdown
# AF Phase H — Consensus Report: Repo Hygiene (BEECRM)

**Security status:** [GREEN/YELLOW/RED]
**Дата:** [дата]

## Инвентаризация (Scout)
| Категория | Всего | Живое | Архив | Удалить | Неясно |
|-----------|-------|-------|-------|---------|--------|
| .playwright-mcp/ | 135 | ? | ? | ? | ? |
| Docs | 4 | ? | ? | ? | ? |
| Scripts | 3 | ? | ? | ? | ? |
| Top-level | 4 | ? | ? | ? | ? |

## Безопасность
| Проблема | Severity | Действие |
|----------|----------|----------|
| CSV с ПД клиентов в .playwright-mcp/ | HIGH | Удалить немедленно |
| .playwright-mcp/ не в .gitignore | MEDIUM | Добавить |
| dashboard/node_modules/ не в .gitignore | LOW | Добавить |

## Cleanup Plan (DevOps)
| Коммит | Действие | Файлов затронуто | Обратимость |
|--------|----------|------------------|-------------|
| 1 | .gitignore update | ? | git revert |
| 2 | .playwright-mcp/ cleanup (ПД) | ? | нет (ПД!) |
| 3 | docs/ archive | ? | git revert |
| 4 | scripts/ organize | ? | git revert |

## Документация обновлена (TechWriter)
- [ ] CLAUDE.md проверен
- [ ] docs/architecture.md обновлен
- [ ] scripts/README.md создан (если решили)
- [ ] MEMORY.md обновлен

## Рекомендация
[конкретные действия для сессии Делатель]

human_decision_required: true
```

Сохрани отчет в `docs/agentforge/report_phaseH_{YYYYMMDD}.md`
