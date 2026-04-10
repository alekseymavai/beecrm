"""apiary/groq_client.py — Groq STT (Whisper) + LLM (Llama) для BEEBOTLITE.

PRIVACY NOTE: Голосовые сообщения и текст осмотра отправляются в облако Groq
(api.groq.com) для распознавания речи и структурирования данных.
Не отправляйте в бот конфиденциальные данные, не связанные с осмотром пасеки.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from groq import AsyncGroq

from apiary.config import GROQ_API_KEY, GROQ_BASE_URL
from apiary.prompts import INSPECTION_PROMPT

logger = logging.getLogger(__name__)

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    return _client


async def transcribe(ogg_bytes: bytes) -> str:
    """Преобразовать голосовое сообщение (ogg/mp3) в текст через Groq Whisper.

    PRIVACY NOTE: аудио уходит в api.groq.com.
    """
    client = _get_client()
    transcription = await client.audio.transcriptions.create(
        file=("voice.ogg", ogg_bytes),
        model="whisper-large-v3",
        language="ru",
        response_format="text",
    )
    return transcription


async def extract_record(text: str, last_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Извлечь структуру осмотра из свободного текста через Groq LLM.

    PRIVACY NOTE: text уходит в api.groq.com.
    Возвращает dict с полями InspectionRecord или {"requires_clarification": true, ...}.
    """
    client = _get_client()
    today = date.today().isoformat()
    last_records_text = json.dumps(last_records, ensure_ascii=False, indent=2) if last_records else "нет"

    prompt = INSPECTION_PROMPT.format(last_records=last_records_text, today=today)

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        temperature=0.1,
        max_tokens=512,
    )

    raw = response.choices[0].message.content.strip()
    # убираем markdown-блок если LLM всё же добавил
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("extract_record: JSON parse error: %s | raw=%r", exc, raw[:200])
        return {
            "requires_clarification": True,
            "clarification_question": "Не смог распознать структуру осмотра. Попробуйте описать кратко: улей, матка, расплод, мёд.",
        }
