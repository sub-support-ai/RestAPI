import bcrypt

# bcrypt — стандарт хэширования паролей.
# Необратим: зная хэш, восстановить пароль невозможно.
# При входе пользователя используем verify() — сравниваем введённый
# пароль с хэшем, не расшифровывая.


def hash_password(password: str) -> str:
    """Превратить пароль в bcrypt-хэш для хранения в БД."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить пароль при входе. Возвращает True если совпадает."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
