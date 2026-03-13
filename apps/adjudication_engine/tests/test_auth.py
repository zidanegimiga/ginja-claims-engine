import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
async def auth_headers(client):
    """Register a test user and return auth headers."""
    await client.post("/api/v1/auth/register", json={
        "email":     "pytest@ginja.ai",
        "password":  "testpassword123",
        "full_name": "Pytest User",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email":    "pytest@ginja.ai",
        "password": "testpassword123",
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_register_success(client):
    res = await client.post("/api/v1/auth/register", json={
        "email":     "new_user@ginja.ai",
        "password":  "password123",
        "full_name": "New User",
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token"  in data
    assert "refresh_token" in data


@pytest.mark.anyio
async def test_register_duplicate_email(client):
    payload = {
        "email":     "duplicate@ginja.ai",
        "password":  "password123",
        "full_name": "Duplicate",
    }
    await client.post("/api/v1/auth/register", json=payload)
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 409


@pytest.mark.anyio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "email":     "login_test@ginja.ai",
        "password":  "password123",
        "full_name": "Login Test",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email":    "login_test@ginja.ai",
        "password": "password123",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.anyio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email":     "wrongpass@ginja.ai",
        "password":  "correctpassword",
        "full_name": "Wrong Pass",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email":    "wrongpass@ginja.ai",
        "password": "wrongpassword",
    })
    assert res.status_code == 401


@pytest.mark.anyio
async def test_me_returns_user(client, auth_headers):
    res = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "pytest@ginja.ai"
    assert data["role"]  == "claims_officer"


@pytest.mark.anyio
async def test_me_unauthenticated(client):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


@pytest.mark.anyio
async def test_refresh_token_rotation(client):
    await client.post("/api/v1/auth/register", json={
        "email":     "refresh@ginja.ai",
        "password":  "password123",
        "full_name": "Refresh Test",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email":    "refresh@ginja.ai",
        "password": "password123",
    })
    refresh_token = login.json()["refresh_token"]

    # First refresh should succeed
    res = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert res.status_code == 200
    new_tokens = res.json()
    assert new_tokens["refresh_token"] != refresh_token

    # Old refresh token should now be invalid
    res2 = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert res2.status_code == 401


@pytest.mark.anyio
async def test_logout_revokes_refresh_token(client):
    await client.post("/api/v1/auth/register", json={
        "email":     "logout@ginja.ai",
        "password":  "password123",
        "full_name": "Logout Test",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email":    "logout@ginja.ai",
        "password": "password123",
    })
    tokens  = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204

    # Refresh token should now be revoked
    res = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"]
    })
    assert res.status_code == 401