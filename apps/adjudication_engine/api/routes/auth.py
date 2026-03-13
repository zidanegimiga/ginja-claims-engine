from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from db.mongo import get_db
from api.models.user import (
    UserCreate, UserLogin, UserResponse,
    TokenPair, RefreshRequest, OAuthUserData
)
from api.services.auth_service import (
    create_user, authenticate_user, get_user_by_id,
    get_or_create_oauth_user, create_token_pair,
    decode_token, store_refresh_token,
    validate_refresh_token, revoke_refresh_token,
)

router  = APIRouter(prefix="/auth", tags=["Authentication"])
bearer  = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db=Depends(get_db),
):
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = await get_user_by_id(db, payload["sub"])
    if not user or not user["is_active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return user


@router.post("/register", response_model=TokenPair, status_code=201)
async def register(body: UserCreate, db=Depends(get_db)):
    try:
        user = await create_user(
            db,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))

    tokens = create_token_pair(user["_id"], user["role"])
    await store_refresh_token(db, user["_id"], tokens.refresh_token)
    return tokens


@router.post("/login", response_model=TokenPair)
async def login(body: UserLogin, db=Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user["is_active"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")

    tokens = create_token_pair(user["_id"], user["role"])
    await store_refresh_token(db, user["_id"], tokens.refresh_token)
    return tokens


@router.post("/oauth", response_model=TokenPair)
async def oauth_login(body: OAuthUserData, db=Depends(get_db)):
    user   = await get_or_create_oauth_user(db, body)
    tokens = create_token_pair(user["_id"], user["role"])
    await store_refresh_token(db, user["_id"], tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db=Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user_id = payload["sub"]

    # Validate against stored hash
    valid = await validate_refresh_token(db, user_id, body.refresh_token)
    if not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")

    user = await get_user_by_id(db, user_id)
    if not user or not user["is_active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    # Issue new pair and rotate stored token
    tokens = create_token_pair(user["_id"], user["role"])
    await store_refresh_token(db, user["_id"], tokens.refresh_token)
    return tokens



@router.post("/logout", status_code=204)
async def logout(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    await revoke_refresh_token(db, current_user["_id"])


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    return UserResponse(
        id=current_user["_id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        is_active=current_user["is_active"],
        created_at=current_user["created_at"],
    )