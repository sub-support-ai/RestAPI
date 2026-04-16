import pytest
from httpx import AsyncClient


# Регистрируем пользователя через /auth/register и возвращаем
# (user_id, access_token) — нужны для тикета и для заголовка Authorization.
async def register_user(client: AsyncClient, suffix: str = "") -> tuple[int, str]:
    response = await client.post("/api/v1/auth/register", json={
        "email": f"ticketuser{suffix}@example.com",
        "username": f"ticketuser{suffix}",
        "password": "secret123",
    })
    assert response.status_code == 201
    token = response.json()["access_token"]

    # /auth/me — узнаём id созданного пользователя
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    return me.json()["id"], token


@pytest.mark.asyncio
async def test_create_ticket(client: AsyncClient):
    user_id, token = await register_user(client, suffix="create")

    response = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "не могу войти в систему",
            "body": "при входе пишет ошибку 403",
            "user_id": user_id,
            "user_priority": 4,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()

    assert data["title"] == "не могу войти в систему"
    assert data["user_id"] == user_id
    assert data["user_priority"] == 4

    assert "id" in data
    assert data["id"] is not None

    # После AI обработки дефолтный статус — pending_user
    assert data["status"] == "pending_user"

    # AI Service в тестах недоступен — приходит заглушка из ai_classifier.py
    assert data["ai_confidence"] == 0.0
    assert data["ai_category"] == "техническая_проблема"


@pytest.mark.asyncio
async def test_list_tickets(client: AsyncClient):
    user_id, token = await register_user(client, suffix="list")
    headers = {"Authorization": f"Bearer {token}"}

    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "первый тикет",
            "body": "описание первого",
            "user_id": user_id,
            "user_priority": 3,
        },
        headers=headers,
    )

    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "второй тикет",
            "body": "описание второго",
            "user_id": user_id,
            "user_priority": 2,
        },
        headers=headers,
    )

    response = await client.get("/api/v1/tickets/", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
