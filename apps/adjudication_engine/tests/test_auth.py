import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from api.main import app


def unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}@ginja.ai"


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest.mark.anyio(scope="module")
async def test_register_success(client: AsyncClient):
    res = await client.post("/api/v1/auth/register", json={
        "email":     unique_email("register"),
        "password":  "password123",
        "full_name": "Register Test",
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token"  in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio(scope="module")
async def test_register_duplicate_email(client: AsyncClient):
    email = unique_email("duplicate")
    payload = {
        "email":     email,
        "password":  "password123",
        "full_name": "Duplicate",
    }
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


@pytest.mark.anyio(scope="module")
async def test_register_short_password_rejected(client: AsyncClient):
    res = await client.post("/api/v1/auth/register", json={
        "email":     unique_email("shortpass"),
        "password":  "123",
        "full_name": "Short Pass",
    })
    assert res.status_code == 422


@pytest.mark.anyio(scope="module")
async def test_login_success(client: AsyncClient):
    email = unique_email("login")
    await client.post("/api/v1/auth/register", json={
        "email":     email,
        "password":  "password123",
        "full_name": "Login Test",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email":    email,
        "password": "password123",
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token"  in data
    assert "refresh_token" in data


@pytest.mark.anyio(scope="module")
async def test_login_wrong_password(client: AsyncClient):
    email = unique_email("wrongpass")
    await client.post("/api/v1/auth/register", json={
        "email":     email,
        "password":  "correctpassword",
        "full_name": "Wrong Pass",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email":    email,
        "password": "wrongpassword",
    })
    assert res.status_code == 401


@pytest.mark.anyio(scope="module")
async def test_login_nonexistent_user(client: AsyncClient):
    res = await client.post("/api/v1/auth/login", json={
        "email":    unique_email("ghost"),
        "password": "password123",
    })
    assert res.status_code == 401


@pytest.mark.anyio(scope="module")
async def test_me_returns_user(client: AsyncClient):
    email = unique_email("me")
    await client.post("/api/v1/auth/register", json={
        "email":     email,
        "password":  "password123",
        "full_name": "Me Test",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email":    email,
        "password": "password123",
    })
    token = login.json()["access_token"]

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"]     == email
    assert data["role"]      == "claims_officer"
    assert data["is_active"] is True


@pytest.mark.anyio(scope="module")
async def test_me_unauthenticated(client: AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.anyio(scope="module")
async def test_me_invalid_token(client: AsyncClient):
    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.valid"},
    )
    assert res.status_code == 401


@pytest.mark.anyio(scope="module")
async def test_refresh_token_rotation(client: AsyncClient):
    email = unique_email("refresh")
    await client.post("/api/v1/auth/register", json={
        "email":     email,
        "password":  "password123",
        "full_name": "Refresh Test",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email":    email,
        "password": "password123",
    })
    old_refresh = login.json()["refresh_token"]

    # First refresh should succeed and return a new pair
    res = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": old_refresh,
    })
    assert res.status_code == 200
    new_tokens = res.json()
    assert "access_token"  in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != old_refresh


@pytest.mark.anyio(scope="module")
async def test_refresh_old_token_rejected_after_rotation(client: AsyncClient):
    email = unique_email("refresh_old")
    await client.post("/api/v1/auth/register", json={
        "email":     email,
        "password":  "password123",
        "full_name": "Refresh Old",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email":    email,
        "password": "password123",
    })
    old_refresh = login.json()["refresh_token"]

    # Rotate once
    await client.post("/api/v1/auth/refresh", json={
        "refresh_token": old_refresh,
    })

    # Old token must now be invalid
    res = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": old_refresh,
    })
    assert res.status_code == 401


@pytest.mark.anyio(scope="module")
async def test_refresh_invalid_token_rejected(client: AsyncClient):
    res = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "not.a.real.token",
    })
    assert res.status_code == 401

@pytest.mark.anyio(scope="module")
async def test_logout_revokes_refresh_token(client: AsyncClient):
    email = unique_email("logout")
    await client.post("/api/v1/auth/register", json={
        "email":     email,
        "password":  "password123",
        "full_name": "Logout Test",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email":    email,
        "password": "password123",
    })
    tokens = login.json()

    # Logout, pass the refresh token so the server knows which to revoke
    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout.status_code == 204

    # Refresh token must be dead after logout
    res = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert res.status_code == 401


@pytest.mark.anyio(scope="module")
async def test_logout_unauthenticated(client: AsyncClient):
    res = await client.post("/api/v1/auth/logout")
    assert res.status_code == 401

