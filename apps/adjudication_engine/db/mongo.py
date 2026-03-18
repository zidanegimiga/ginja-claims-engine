import os
import asyncio
from dotenv import load_dotenv
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from datetime import datetime, timezone

load_dotenv()

_client = None
_db     = None
_loop   = None



def get_database():
    """
    Returns the MongoDB database instance.
    Recreates the client if the event loop has changed —
    this prevents 'Event loop is closed' errors when
    multiple test modules run sequentially.
    """
    global _client, _db, _loop

    try:
        current_loop = asyncio.get_event_loop()
    except RuntimeError:
        current_loop = None

    if _db is None or _loop != current_loop:
        if _client is not None:
            _client.close()
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DB_NAME", "ginja_claims")
        _client = AsyncIOMotorClient(uri)
        _db = _client[db_name]
        _loop = current_loop

    return _db

async def save_adjudication_result(result: dict) -> None:
    """
    Saves a completed adjudication result to MongoDB.
    Raises on failure so the caller knows the save did not complete.
    """
    db = get_database()
    collection = db["claims"]

    if "adjudicated_at" not in result:
        result["adjudicated_at"] = datetime.now(timezone.utc).isoformat()

    await collection.update_one(
        {"claim_id": result["claim_id"]},
        {"$set": result},
        upsert=True,
    )


async def get_adjudication_result(claim_id: str) -> dict | None:
    """
    Retrieves a single adjudication result by claim ID.
    Raises on failure rather than silently returning None.
    """
    db = get_database()
    collection = db["claims"]
    return await collection.find_one(
        {"claim_id": claim_id},
        {"_id": 0},
    )


async def list_adjudication_results(
    decision: str | None = None,
    limit: int = 20,
    skip: int = 0,
) -> tuple[int, list[dict]]:
    db = get_database()
    collection = db["claims"]

    query = {}
    if decision:
        query["decision"] = decision

    total  = await collection.count_documents(query)
    cursor = collection.find(query, {"_id": 0}).sort("adjudicated_at", -1).skip(skip).limit(limit)
    results = await cursor.to_list(length=limit)

    return total, results

async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    FastAPI dependency that yields the database instance.
    Wraps the existing get_database() singleton so all new
    routes can use Depends(get_db) without touching the
    existing save/list/get functions.
    """
    yield get_database()
