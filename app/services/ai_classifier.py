import json
import logging

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
    Отправляет тикет в AI Service, получает классификацию от Llama 3.3 70B.

    Склеиваем title и body в одну строку — AI Lead попросил
    присылать готовый текст в поле ticket_text.
    """
    ticket_text = f"{title}\n\n{body}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/ai/classify",
                json={
                    "ticket_id": ticket_id,
                    "ticket_text": ticket_text,
                },
            )
            response.raise_for_status()
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.warning(
                    "AI Service вернул невалидный JSON для classify",
                    extra={"ticket_id": ticket_id},
                    exc_info=True,
                )
                return dict(_CLASSIFICATION_FALLBACK)

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
        return dict(_CLASSIFICATION_FALLBACK)
