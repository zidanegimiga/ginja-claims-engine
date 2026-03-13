import pytest
import os
from httpx import AsyncClient, ASGITransport
from api.main import app


VALID_CLAIM = {
    "member_id":       "M-TEST-001",
    "provider_id":     "P-TEST-001",
    "diagnosis_code":  "A09",
    "procedure_code":  "99213",
    "claimed_amount":  5000.0,
    "approved_tariff": 4500.0,
    "date_of_service": "2026-03-01",
    "provider_type":   "clinic",
    "location":        "Nairobi",
    "member_age":      35,
}


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


@pytest.fixture(scope="module")
def api_headers():
    key = os.environ.get("API_KEY_PRIMARY", "")
    if not key:
        pytest.skip("API_KEY_PRIMARY not set — skipping adjudication tests")
    return {"X-API-Key": key}


# ── Batch 1 — Basic adjudication ─────────────────────────────────────────────

@pytest.mark.anyio(scope="module")
async def test_adjudicate_valid_claim(client: AsyncClient, api_headers: dict):
    res = await client.post(
        "/api/v1/adjudicate",
        json=VALID_CLAIM,
        headers=api_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision"] in ("Pass", "Flag", "Fail")
    assert 0 <= data["risk_score"] <= 1
    assert "claim_id"               in data
    assert "feature_contributions"  in data
    assert "explanation_of_benefits" in data


@pytest.mark.anyio(scope="module")
async def test_adjudicate_no_api_key_rejected(client: AsyncClient):
    res = await client.post("/api/v1/adjudicate", json=VALID_CLAIM)
    assert res.status_code == 401


@pytest.mark.anyio(scope="module")
async def test_adjudicate_missing_required_field(client: AsyncClient, api_headers: dict):
    claim = {k: v for k, v in VALID_CLAIM.items() if k != "member_id"}
    res   = await client.post(
        "/api/v1/adjudicate",
        json=claim,
        headers=api_headers,
    )
    assert res.status_code == 422

@pytest.mark.anyio(scope="module")
async def test_adjudicate_persists_claim_fields(client: AsyncClient, api_headers: dict):
    res = await client.post(
        "/api/v1/adjudicate",
        json=VALID_CLAIM,
        headers=api_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["member_id"]      == VALID_CLAIM["member_id"]
    assert data["provider_id"]    == VALID_CLAIM["provider_id"]
    assert data["claimed_amount"] == VALID_CLAIM["claimed_amount"]
    assert data["diagnosis_code"] == VALID_CLAIM["diagnosis_code"]
    assert data["location"]       == VALID_CLAIM["location"]


@pytest.mark.anyio(scope="module")
async def test_adjudicate_future_date_rejected(client: AsyncClient, api_headers: dict):
    claim = {**VALID_CLAIM, "date_of_service": "2099-01-01"}
    res   = await client.post(
        "/api/v1/adjudicate",
        json=claim,
        headers=api_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision"]           == "Fail"
    assert data["adjudication_stage"] == 1


@pytest.mark.anyio(scope="module")
async def test_adjudicate_high_amount_flagged(client: AsyncClient, api_headers: dict):
    claim = {
        **VALID_CLAIM,
        "claimed_amount":  500_000.0,
        "approved_tariff": 5_000.0,
    }
    res = await client.post(
        "/api/v1/adjudicate",
        json=claim,
        headers=api_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision"] in ("Flag", "Fail")

@pytest.mark.anyio(scope="module")
async def test_adjudicate_with_patient_details(client: AsyncClient, api_headers: dict):
    claim = {
        **VALID_CLAIM,
        "patient": {
            "full_name":     "Jane Doe",
            "national_id":   "123456789",
            "date_of_birth": "1990-01-15",
        },
        "source": {
            "source_type": "manual",
        },
    }
    res = await client.post(
        "/api/v1/adjudicate",
        json=claim,
        headers=api_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["patient"]["full_name"]  == "Jane Doe"
    assert data["patient"]["national_id"] == "123456789"


@pytest.mark.anyio(scope="module")
async def test_adjudicate_with_invoice_number(client: AsyncClient, api_headers: dict):
    claim = {
        **VALID_CLAIM,
        "invoice_number": "INV-2026-001",
        "source": {
            "source_type": "manual",
        },
    }
    res = await client.post(
        "/api/v1/adjudicate",
        json=claim,
        headers=api_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["invoice_number"]        == "INV-2026-001"
    assert data["source"]["source_type"] == "manual"


@pytest.mark.anyio(scope="module")
async def test_claim_retrievable_after_adjudication(client: AsyncClient, api_headers: dict):
    res = await client.post(
        "/api/v1/adjudicate",
        json=VALID_CLAIM,
        headers=api_headers,
    )
    assert res.status_code == 200, res.text
    claim_id = res.json()["claim_id"]

    get_res = await client.get(
        f"/api/v1/claims/{claim_id}",
        headers=api_headers,
    )
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["claim_id"] == claim_id
    assert data["member_id"] == VALID_CLAIM["member_id"]
    assert data["claimed_amount"] == VALID_CLAIM["claimed_amount"]
