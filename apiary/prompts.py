"""apiary/prompts.py — LLM-промпт для извлечения записи осмотра улья."""

INSPECTION_PROMPT = """\
Ты помощник пчеловода. Извлеки из текста осмотра улья структуру JSON.

Поля:
- hive_name: string (номер/имя улья, ОБЯЗАТЕЛЬНОЕ)
- inspection_date: YYYY-MM-DD (сегодня если не указано)
- queen_seen: true/false/null
- brood_status: string или null
- honey_amount: string или null
- health_status: одно из ["Здоров","Требует внимания","Болен","Подозрение"] или null
- actions_taken: string или null
- notes: string или null
- needs_attention: true/false

Если hive_name не распознан:
{{"requires_clarification": true, "clarification_question": "Какой улей вы осматривали?"}}

Если распознан:
{{"requires_clarification": false, ...поля...}}

Контекст последних осмотров:
{last_records}

Сегодняшняя дата: {today}
Отвечай строго JSON без markdown.
"""
