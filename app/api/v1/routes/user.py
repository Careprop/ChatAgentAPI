import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import verify_api_key
from app.api.v1.dependencies.db import get_db
from app.api.v1.dependencies.rate_limit import limiter
from app.api.v1.schemas.user import UserCreate, UserResponse
from app.repositories.user import UserRepository

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
@limiter.limit("60/minute")
async def create_user(
    request: Request,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    repo = UserRepository(db)
    if await repo.get_by_username(payload.username):
        raise HTTPException(409, "Username already taken")
    user = await repo.create(payload.username)
    await db.commit()
    return UserResponse.model_validate(user)


@router.get("", response_model=UserResponse)
async def get_user_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    repo = UserRepository(db)
    user = await repo.get_by_username(username)
    if not user:
        raise HTTPException(404, "User not found")
    return UserResponse.model_validate(user)


@router.get("/{external_id}", response_model=UserResponse)
async def get_user(
    external_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    repo = UserRepository(db)
    user = await repo.get_by_external_id(external_id)
    if not user:
        raise HTTPException(404, "User not found")
    return UserResponse.model_validate(user)
