import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()

def test_connection():
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME")

    print(f"Connecting to database: {db_name}")

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[db_name]
        collections = db.list_collection_names()
        print(f"Connection successful")
        print(f"Collections found: {collections}")
        client.close()
    except ConnectionFailure as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_connection()