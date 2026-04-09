
# bcrypt — стандарт хэширования паролей.
# Необратим: зная хэш, восстановить пароль невозможно.
# При входе пользователя используем verify() — сравниваем введённый
# пароль с хэшем, не расшифровывая.


from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


# ── Пароли ────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Превратить пароль в bcrypt-хэш для хранения в БД."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить пароль при входе. True если совпадает."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


# ── JWT токены ────────────────────────────────────────────────────────────────

def create_access_token(user_id: int, role: str) -> str:
    """
    Создать JWT токен для пользователя.
    Внутри токена зашиты: id пользователя, его роль, время истечения.
    Токен подписан секретным ключом — подделать нельзя.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),   # sub = subject, стандартное поле JWT
        "role": role,
        "exp": expire,         # exp = expiration, когда токен истекает
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Расшифровать токен и вернуть данные внутри.
    Если токен неверный или истёк — выбросит JWTError.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])