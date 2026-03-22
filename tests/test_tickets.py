import pytest
from httpx import AsyncClient

# Вспомогательная функция — создаёт пользователя и возвращает его id.
# Нужна потому что тикет требует user_id.
# Выносим в отдельную функцию чтобы не повторять в каждом тесте.
async def create_user(client: AsyncClient, suffix: str = "") -> int:
    response = await client.post("/api/v1/users/", json={
        "email": f"ticketuser{suffix}@example.com",
        "username": f"ticketuser{suffix}",
        "password": "secret123",
    })
    return response.json()["id"]

@pytest.mark.asyncio
async def test_create_ticket(client: AsyncClient):
    # Сначала создаём пользователя — тикет требует user_id
    user_id = await create_user(client, suffix="create")

    # Отправляем запрос на создание тикета
    response = await client.post("/api/v1/tickets/", json={
        "title": "не могу войти в систему",
        "body": "при входе пишет ошибку 403",
        "user_id": user_id,
        "user_priority": 4,
    })

    # Проверяем статус ответа — должен быть 201 Created
    assert response.status_code == 201
    data = response.json()

    # Проверяем что данные сохранились правильно
    assert data["title"] == "не могу войти в систему"
    assert data["user_id"] == user_id
    assert data["user_priority"] == 4

    # Проверяем что id появился — база его присвоила
    assert "id" in data
    assert data["id"] is not None

    # Проверяем статус — после AI обработки должен быть pending_user
    assert data["status"] == "pending_user"

    # Проверяем AI поля — они заполнены заглушкой (AI Service не запущен)
    # confidence = 0.0 означает что пришла заглушка из ai_classifier.py
    assert data["ai_confidence"] == 0.0
    assert data["ai_category"] == "техническая_проблема"

@pytest.mark.asyncio
async def test_list_tickets(client: AsyncClient):
    # Создаём пользователя и два тикета
    user_id = await create_user(client, suffix="list")

    await client.post("/api/v1/tickets/", json={
        "title": "первый тикет",
        "body": "описание первого",
        "user_id": user_id,
        "user_priority": 3,
    })

    await client.post("/api/v1/tickets/", json={
        "title": "второй тикет",
        "body": "описание второго",
        "user_id": user_id,
        "user_priority": 2,
    })

    # Запрашиваем список
    response = await client.get("/api/v1/tickets/")
    assert response.status_code == 200

    data = response.json()

    # Список — это массив
    assert isinstance(data, list)

    # Создали два — должны получить минимум два
    assert len(data) >= 2