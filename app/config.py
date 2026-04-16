from functools import lru_cache
from dotenv import load_dotenv
import os

load_dotenv()

# Маркер дефолтного небезопасного JWT_SECRET_KEY. В production запрещён —
# разворачиваем self-hosted у клиента, и дефолтный ключ = полная потеря
# безопасности токенов.
_DEFAULT_JWT_SECRET = "supersecretkey_change_in_production"


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "app_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://ai-service:8001")

    # Секретный ключ для подписи JWT токенов
    # В продакшне — длинная случайная строка, хранится в .env
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", _DEFAULT_JWT_SECRET)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", 60))

    def __post_init_check__(self) -> None:
        # При self-hosted развёртывании у клиента (слайд 6 презентации)
        # дефолтный ключ недопустим — любой с доступом к репозиторию
        # сможет выпускать валидные токены.
        if self.APP_ENV == "production" and self.JWT_SECRET_KEY == _DEFAULT_JWT_SECRET:
            raise RuntimeError(
                "JWT_SECRET_KEY не задан в .env при APP_ENV=production. "
                "Сгенерируй длинную случайную строку и положи в переменные окружения."
            )

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.__post_init_check__()
    return s
