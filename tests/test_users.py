import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthcheck(client: AsyncClient):
    response = await client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """POST /auth/register — самостоятельная регистрация. Возвращает access_token."""
    payload = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "secret123",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Проверяем, что пароль не утекает в /auth/me
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["email"] == payload["email"]
    assert me_data["username"] == payload["username"]
    assert me_data["role"] == "user"
    assert me_data["is_active"] is True
    assert "password" not in me_data
    assert "hashed_password" not in me_data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "username": "user1",
        "password": "secret123",
    }
    await client.post("/api/v1/auth/register", json=payload)

    # Второй раз с тем же email — 409
    payload["username"] = "user2"
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "Email" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    payload = {
        "email": "user3@example.com",
        "username": "sameusername",
        "password": "secret123",
    }
    await client.post("/api/v1/auth/register", json=payload)

    # Второй раз с тем же username — 409
    payload["email"] = "user4@example.com"
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "Username" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_self(client: AsyncClient):
    """GET /users/{id} доступен владельцу — /users/<свой_id> возвращает 200."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": "getme@example.com",
        "username": "getmeuser",
        "password": "secret123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    user_id = me.json()["id"]

    response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == user_id


@pytest.mark.asyncio
async def test_get_other_user_forbidden(client: AsyncClient):
    """Обычный пользователь не может смотреть чужой профиль → 403."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": "spy@example.com",
        "username": "spy",
        "password": "secret123",
    })
    token = reg.json()["access_token"]
    response = await client.get(
        "/api/v1/users/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_users_list_requires_admin(client: AsyncClient):
    """GET /users/ без админ-токена → 403."""
    reg = await client.post("/api/v1/auth/register", json={
        "email": "nonadmin@example.com",
        "username": "nonadmin",
        "password": "secret123",
    })
    token = reg.json()["access_token"]
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_stats_requires_auth(client: AsyncClient):
    """GET /stats/ без токена → 401."""
    response = await client.get("/api/v1/stats/")
    assert response.status_code == 401
