import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.models.user import UserRole, TokenPair, OAuthUserData

import os

SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY = 15 # minutes
REFRESH_TOKEN_EXPIRY = 7 * 24 * 60  # 7 days in minutes


# Password hashing
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# Token creation

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRY)
    return jwt.encode(
        {"sub": user_id, "role": role, "type": "access", "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRY)
    return jwt.encode(
        {
            "sub":  user_id,
            "type": "refresh",
            "exp":  expire,
            "jti":  str(uuid.uuid4()),   # unique ID — prevents identical tokens
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_token_pair(user_id: str, role: str) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user_id, role),
        refresh_token=create_refresh_token(user_id),
    )


# Token validation

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# User operations

async def create_user(
    db: AsyncIOMotorDatabase,
    email: str,
    password: str,
    full_name: str,
    role: UserRole = UserRole.claims_officer,
) -> dict:
    existing = await db.users.find_one({"email": email})
    if existing:
        raise ValueError("Email already registered")

    user = {
        "_id": str(uuid.uuid4()),
        "email": email.lower(),
        "password_hash": hash_password(password),
        "full_name": full_name,
        "role": role.value,
        "is_active": True,
        "provider": "credentials",
        "provider_id": None,
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
        "image": None,
    }
    await db.users.insert_one(user)
    return user


async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[dict]:
    return await db.users.find_one({"email": email.lower()})


async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str) -> Optional[dict]:
    return await db.users.find_one({"_id": user_id})


async def authenticate_user(
    db: AsyncIOMotorDatabase, email: str, password: str
) -> Optional[dict]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if user.get("provider") != "credentials":
        return None  # OAuth user trying credentials login
    if not verify_password(password, user["password_hash"]):
        return None
    return user


async def get_or_create_oauth_user(
    db: AsyncIOMotorDatabase, data: OAuthUserData
) -> dict:
    full_name = data.full_name or data.email.split("@")[0]

    # Look up by provider + provider_id first
    user = await db.users.find_one({
        "provider":    data.provider,
        "provider_id": data.provider_id,
    })
    if user:
        # Always refresh image in case it changed
        if data.image:
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"image": data.image, "last_login": datetime.now(timezone.utc)}}
            )
            user["image"] = data.image
        return user

    # Fall back to email match
    user = await db.users.find_one({"email": data.email.lower()})
    if user:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "provider": data.provider,
                "provider_id": data.provider_id,
                "image": data.image,
                "last_login":  datetime.now(timezone.utc),
            }}
        )
        user["image"] = data.image
        return user

    # New OAuth user
    user = {
        "_id": str(uuid.uuid4()),
        "email": data.email.lower(),
        "password_hash": None,
        "full_name": full_name,
        "image": data.image,
        "role": UserRole.viewer.value,
        "is_active": True,
        "provider": data.provider,
        "provider_id": data.provider_id,
        "created_at": datetime.now(timezone.utc),
        "last_login": datetime.now(timezone.utc),
    }
    await db.users.insert_one(user)
    return user

async def store_refresh_token(
    db: AsyncIOMotorDatabase, user_id: str, token: str
) -> None:
    """Store hashed refresh token as its own record — one row per token."""
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await db.refresh_tokens.insert_one({
        "user_id": user_id,
        "token_hash": token_hash,
        "created_at": datetime.now(timezone.utc),
    })


async def validate_refresh_token(
    db: AsyncIOMotorDatabase, user_id: str, token: str
) -> bool:
    """Return True only if this exact token hash exists in the store."""
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    record = await db.refresh_tokens.find_one({
        "user_id": user_id,
        "token_hash": token_hash,
    })
    return record is not None


async def revoke_refresh_token(
    db: AsyncIOMotorDatabase, user_id: str, token: str
) -> None:
    """Delete this specific token — not all tokens for the user."""
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await db.refresh_tokens.delete_one({
        "user_id": user_id,
        "token_hash": token_hash,
    })