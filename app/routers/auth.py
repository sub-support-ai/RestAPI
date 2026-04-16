from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import TokenResponse, UserMe
from app.schemas.user import UserCreate
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


# ── POST /auth/login — войти и получить токен ─────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),  # стандартная форма: username + password
    db: AsyncSession = Depends(get_db),
):
    # Ищем пользователя по username
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()

    # Если не нашли или пароль неверный — одна и та же ошибка
    # (не говорим что именно неверно — безопаснее)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован",
        )

    # Создаём токен и возвращаем
    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(access_token=token)


# ── POST /auth/register — регистрация + сразу токен ───────────────────────────
@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создаёт нового пользователя и сразу выдаёт access token,
    чтобы не делать лишний POST /auth/login после регистрации.
    """
    # Уникальность email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Уникальность username
    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(access_token=token)


# ── GET /auth/me — кто я? ─────────────────────────────────────────────────────
@router.get("/me", response_model=UserMe)
async def get_me(current_user: User = Depends(get_current_user)):
    """Вернуть данные текущего авторизованного пользователя."""
    return current_user