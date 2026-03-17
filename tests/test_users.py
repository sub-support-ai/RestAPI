import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthcheck(client: AsyncClient):
    response = await client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    payload = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "secret123",
    }
    response = await client.post("/api/v1/users/", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == payload["email"]
    assert data["username"] == payload["username"]
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data
    # Пароль не должен утекать в ответе
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "username": "user1",
        "password": "secret123",
    }
    await client.post("/api/v1/users/", json=payload)

    # Второй раз с тем же email — должен вернуть 409
    payload["username"] = "user2"
    response = await client.post("/api/v1/users/", json=payload)
    assert response.status_code == 409
    assert "Email" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_duplicate_username(client: AsyncClient):
    payload = {
        "email": "user3@example.com",
        "username": "sameusername",
        "password": "secret123",
    }
    await client.post("/api/v1/users/", json=payload)

    # Второй раз с тем же username — должен вернуть 409
    payload["email"] = "user4@example.com"
    response = await client.post("/api/v1/users/", json=payload)
    assert response.status_code == 409
    assert "Username" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user(client: AsyncClient):
    # Создаём пользователя
    create_response = await client.post("/api/v1/users/", json={
        "email": "getme@example.com",
        "username": "getmeuser",
        "password": "secret123",
    })
    user_id = create_response.json()["id"]

    # Получаем по id
    response = await client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["id"] == user_id


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    response = await client.get("/api/v1/users/99999")
    assert response.status_code == 404
