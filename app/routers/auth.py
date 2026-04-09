from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserMe
from app.security import create_access_token, decode_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Говорим FastAPI: токен берётся из заголовка Authorization: Bearer <токен>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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


# ── Dependency: получить текущего пользователя из токена ──────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Это не эндпоинт — это зависимость (Depends).
    Любой роутер может написать Depends(get_current_user)
    и автоматически получить объект текущего пользователя.
    Если токен неверный — вернёт 401 автоматически.
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Токен недействителен или истёк",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_error

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_error

    return user


# ── GET /auth/me — кто я? ─────────────────────────────────────────────────────
@router.get("/me", response_model=UserMe)
async def get_me(current_user: User = Depends(get_current_user)):
    """Вернуть данные текущего авторизованного пользователя."""
    return current_user