import httpx
from app.config import get_settings

settings = get_settings()

AI_SERVICE_URL = settings.AI_SERVICE_URL

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
                }
            )
            response.raise_for_status()
            return response.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
        # AI Service ещё не поднят — возвращаем заглушку
        # Убрать когда AI Lead поднимет эндпоинт
        return {
            "category": "техническая_проблема",
            "priority": "средний",
            "confidence": 0.0,
            "draft_response": "[AI Service недоступен — требует агента]"
        }