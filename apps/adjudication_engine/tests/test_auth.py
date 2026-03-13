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