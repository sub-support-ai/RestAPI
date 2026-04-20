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
            # user_id НЕ передаём — он берётся из JWT (current_user.id)
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
            "user_priority": 3,
        },
        headers=headers,
    )

    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "второй тикет",
            "body": "описание второго",
            "user_priority": 2,
        },
        headers=headers,
    )

    response = await client.get("/api/v1/tickets/", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


# ── Ownership: пользователь не должен видеть чужие тикеты ─────────────────────

@pytest.mark.asyncio
async def test_list_tickets_returns_only_own(client: AsyncClient):
    """
    Два пользователя, каждый создаёт свой тикет.
    GET /tickets/ должен вернуть КАЖДОМУ только его тикет, не оба.
    """
    _, token_alice = await register_user(client, suffix="alice")
    _, token_bob = await register_user(client, suffix="bob")

    # Alice создаёт свой
    await client.post(
        "/api/v1/tickets/",
        json={"title": "тикет алисы", "body": "секрет алисы", "user_priority": 3},
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    # Bob создаёт свой
    await client.post(
        "/api/v1/tickets/",
        json={"title": "тикет боба", "body": "секрет боба", "user_priority": 3},
        headers={"Authorization": f"Bearer {token_bob}"},
    )

    # Alice видит только свои тикеты
    resp = await client.get(
        "/api/v1/tickets/",
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    assert resp.status_code == 200
    titles = {t["title"] for t in resp.json()}
    assert "тикет алисы" in titles
    assert "тикет боба" not in titles


@pytest.mark.asyncio
async def test_get_other_user_ticket_returns_404(client: AsyncClient):
    """
    Alice создаёт тикет, Bob пытается запросить его по ID → 404
    (именно 404, а не 403 — не палим существование тикета).
    """
    _, token_alice = await register_user(client, suffix="owngetA")
    _, token_bob = await register_user(client, suffix="owngetB")

    # Alice создаёт тикет и запоминает его id
    create = await client.post(
        "/api/v1/tickets/",
        json={"title": "чужой", "body": "чужой", "user_priority": 3},
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    alice_ticket_id = create.json()["id"]

    # Bob пытается его прочитать
    resp = await client.get(
        f"/api/v1/tickets/{alice_ticket_id}",
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_resolve_other_user_ticket(client: AsyncClient):
    """Bob не может закрыть тикет Alice → 404."""
    _, token_alice = await register_user(client, suffix="resA")
    _, token_bob = await register_user(client, suffix="resB")

    create = await client.post(
        "/api/v1/tickets/",
        json={"title": "чужой resolve", "body": "чужой", "user_priority": 3},
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    alice_ticket_id = create.json()["id"]

    resp = await client.patch(
        f"/api/v1/tickets/{alice_ticket_id}/resolve",
        json={"agent_accepted_ai_response": True},
        headers={"Authorization": f"Bearer {token_bob}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_user_id_in_body_is_ignored(client: AsyncClient):
    """
    Даже если клиент подпихнёт user_id в JSON — он должен быть проигнорирован.
    Схема Pydantic его не принимает (extra fields разрешены, но не парсятся).
    Проверяем: ticket.user_id == current_user.id из токена.
    """
    alice_id, token_alice = await register_user(client, suffix="spoofA")
    bob_id, token_bob = await register_user(client, suffix="spoofB")

    # Alice создаёт тикет, пытается подставить user_id Боба
    resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "попытка спуфа",
            "body": "хочу создать от имени боба",
            "user_priority": 3,
            "user_id": bob_id,  # ← попытка атаки
        },
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    assert resp.status_code == 201
    # В базе тикет принадлежит Alice, а не Bob
    assert resp.json()["user_id"] == alice_id
    assert resp.json()["user_id"] != bob_id
