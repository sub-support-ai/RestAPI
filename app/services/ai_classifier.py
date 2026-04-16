import json
import logging
import time

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

AI_SERVICE_URL = settings.AI_SERVICE_URL

_CLASSIFICATION_FALLBACK = {
    "category": "техническая_проблема",
    "priority": "средний",
    "confidence": 0.0,
    "draft_response": "[AI Service недоступен — требует агента]",
}


async def classify_ticket(ticket_id: int, title: str, body: str) -> dict:
    """
    Отправляет тикет в AI Service, получает классификацию от Mistral.

    В ответ кладём `response_time_ms` — длительность вызова в миллисекундах.
    Используется в AILog.ai_response_time_ms для метрик (питч-дек обещает
    среднее время 1,01 сек — честно считаем по этому полю).
    """
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/ai/classify",
                json={
                    "ticket_id": ticket_id,
                    "title": title,
                    "body": body,
                },
            )
            response.raise_for_status()
            try:
                data = response.json()
            except json.JSONDecodeError:
                logger.warning(
                    "AI Service вернул невалидный JSON для classify",
                    extra={"ticket_id": ticket_id},
                    exc_info=True,
                )
                data = dict(_CLASSIFICATION_FALLBACK)

    except (
        httpx.ConnectError,
        httpx.TimeoutException,
        httpx.HTTPStatusError,
        httpx.UnsupportedProtocol,
    ) as e:
        logger.warning(
            "AI Service недоступен или ответ с ошибкой: %s",
            e,
            extra={"ticket_id": ticket_id},
        )
        data = dict(_CLASSIFICATION_FALLBACK)

    data["response_time_ms"] = int((time.perf_counter() - started) * 1000)
    return data
