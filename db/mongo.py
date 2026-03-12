import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

_client = None
_db = None


def get_database():
    """
    Returns the MongoDB database instance.
    Uses a module-level singleton so we don't
    create a new connection on every request.
    """
    global _client, _db
    if _db is None:
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DB_NAME", "ginja_claims")
        _client = AsyncIOMotorClient(uri)
        _db = _client[db_name]
    return _db


async def save_adjudication_result(result: dict) -> None:
    """
    Saves a completed adjudication result to MongoDB.
    Uses claim_id as the document identifier so
    re-adjudicating a claim updates the existing record.
    """
    try:
        db = get_database()
        collection = db["claims"]
        await collection.update_one(
            {"claim_id": result["claim_id"]},
            {"$set": result},
            upsert=True,
        )
    except Exception as e:
        # Log but don't crash. Saving to DB should never prevent a claim from being adjudicated
        print(f"MongoDB save error: {e}")


async def get_adjudication_result(claim_id: str) -> dict | None:
    """
    Retrieves a single adjudication result by claim ID.
    Returns None if not found.
    """
    try:
        db  = get_database()
        collection = db["claims"]
        result = await collection.find_one(
            {"claim_id": claim_id},
            {"_id": 0},
        )
        return result
    except Exception as e:
        print(f"MongoDB fetch error: {e}")
        return None


async def list_adjudication_results(
    decision: str | None = None,
    limit: int = 20,
    skip: int = 0,
) -> list[dict]:
    """
    Returns a paginated list of adjudication results.
    Optionally filtered by decision type.
    """
    try:
        db = get_database()
        collection = db["claims"]
        query  = {}
        if decision:
            query["decision"] = decision
        cursor = collection.find(query, {"_id": 0}).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception as e:
        print(f"MongoDB list error: {e}")
        return []