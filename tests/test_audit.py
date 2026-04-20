"""Тесты для audit_log.

Что проверяем:
  1) Важные события пишутся: успешная регистрация, создание/удаление тикета.
  2) Неудачный логин пишется тоже (несмотря на HTTPException + rollback).
  3) GET /audit доступен только admin'у.
"""

import json

import pytest
from httpx import AsyncClient


async def register(client: AsyncClient, suffix: str, bootstrap_admin: bool = False):
    """Зарегистрировать юзера; вернуть (id, token).
    Если bootstrap_admin=True — через monkeypatch эта регистрация станет админом
    (логика в routers/auth.py). Здесь мы просто регистрируем обычного.
    """
    r = await client.post("/api/v1/auth/register", json={
        "email": f"audit{suffix}@example.com",
        "username": f"audit{suffix}",
        "password": "secret123",
    })
    assert r.status_code == 201
    token = r.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return me.json()["id"], token


@pytest.mark.asyncio
async def test_register_is_audited(client: AsyncClient):
    """POST /auth/register → в audit_logs строка action='user.register'."""
    user_id, token = await register(client, "reg")

    # Чтобы посмотреть журнал, нужен admin. Промоутим через bootstrap.
    from app.config import get_settings
    import pytest as _pytest  # чтобы не путать с именем параметра в других тестах
    settings = get_settings()
    # Временный admin-аккаунт только для чтения журнала.
    settings.BOOTSTRAP_ADMIN_EMAIL = "auditadmin@example.com"
    admin_r = await client.post("/api/v1/auth/register", json={
        "email": "auditadmin@example.com",
        "username": "auditadmin",
        "password": "secret123",
    })
    admin_token = admin_r.json()["access_token"]
    settings.BOOTSTRAP_ADMIN_EMAIL = None

    audit = await client.get(
        f"/api/v1/audit/?user_id={user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert audit.status_code == 200
    events = audit.json()

    register_events = [e for e in events if e["action"] == "user.register"]
    assert len(register_events) == 1
    e = register_events[0]
    assert e["user_id"] == user_id
    assert e["ip"] is not None
    # details — JSON-строка, проверяем валидность и содержимое
    details = json.loads(e["details"])
    assert details["role"] == "user"


@pytest.mark.asyncio
async def test_failed_login_is_audited_despite_rollback(client: AsyncClient):
    """
    Главный нюанс, который мы специально обрабатывали в auth.py:
    неудачный логин бросает 401, get_db делает rollback — но мы коммитим
    audit ЯВНО перед raise, поэтому запись должна сохраниться.
    """
    # Создаём юзера с известным паролем
    _, _ = await register(client, "fail")

    # Три заведомо неверные попытки (не 5, чтобы не упереться в rate limit)
    for _ in range(3):
        r = await client.post(
            "/api/v1/auth/login",
            data={"username": "auditfail", "password": "wrong"},
        )
        assert r.status_code == 401

    # Промоутим временного админа, как в предыдущем тесте
    from app.config import get_settings
    settings = get_settings()
    settings.BOOTSTRAP_ADMIN_EMAIL = "auditadmin2@example.com"
    admin_r = await client.post("/api/v1/auth/register", json={
        "email": "auditadmin2@example.com",
        "username": "auditadmin2",
        "password": "secret123",
    })
    admin_token = admin_r.json()["access_token"]
    settings.BOOTSTRAP_ADMIN_EMAIL = None

    audit = await client.get(
        "/api/v1/audit/?action=login.failure",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert audit.status_code == 200
    fails = audit.json()
    # Три неудачные попытки с username='auditfail' — должны быть записаны
    our_fails = [
        e for e in fails
        if e["details"] and json.loads(e["details"]).get("username") == "auditfail"
    ]
    assert len(our_fails) == 3


@pytest.mark.asyncio
async def test_ticket_delete_is_audited(client: AsyncClient):
    """DELETE /tickets/{id} → в audit_logs action='ticket.delete' c target_id."""
    # Создаём обычного юзера + тикет
    user_id, user_token = await register(client, "owner")
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={"title": "to be deleted", "body": "test", "user_priority": 3},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert ticket_resp.status_code == 201
    ticket_id = ticket_resp.json()["id"]

    # Бутстрапим админа и удаляем
    from app.config import get_settings
    settings = get_settings()
    settings.BOOTSTRAP_ADMIN_EMAIL = "auditadmin3@example.com"
    admin_r = await client.post("/api/v1/auth/register", json={
        "email": "auditadmin3@example.com",
        "username": "auditadmin3",
        "password": "secret123",
    })
    admin_token = admin_r.json()["access_token"]
    settings.BOOTSTRAP_ADMIN_EMAIL = None

    del_r = await client.delete(
        f"/api/v1/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_r.status_code == 204

    audit = await client.get(
        f"/api/v1/audit/?action=ticket.delete",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert audit.status_code == 200
    deletes = [e for e in audit.json() if e["target_id"] == ticket_id]
    assert len(deletes) == 1
    e = deletes[0]
    assert e["target_type"] == "ticket"
    details = json.loads(e["details"])
    assert details["owner_user_id"] == user_id


@pytest.mark.asyncio
async def test_audit_endpoint_forbidden_for_non_admin(client: AsyncClient):
    """GET /audit обычному юзеру → 403."""
    _, token = await register(client, "nonadmin")
    r = await client.get("/api/v1/audit/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_audit_endpoint_requires_auth(client: AsyncClient):
    """GET /audit без токена → 401."""
    r = await client.get("/api/v1/audit/")
    assert r.status_code == 401
