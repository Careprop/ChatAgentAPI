import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
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
    response: Response,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    repo = UserRepository(db)
    if await repo.get_by_client_id(payload.client_id):
        raise HTTPException(409, "client_id already taken")
    user = await repo.create(payload.client_id, display_name=payload.display_name, token_budget=payload.token_budget)
    await db.commit()
    return UserResponse.model_validate(user)


@router.get("", response_model=UserResponse)
async def get_user_by_client_id(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    repo = UserRepository(db)
    user = await repo.get_by_client_id(client_id)
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
