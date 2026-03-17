from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
import app.models  # noqa: F401 — регистрирует все 5 моделей в Base.metadata
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаём все таблицы при старте если их нет.
    # В продакшне это делается через Alembic-миграции.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Закрываем все соединения с БД при остановке сервера
    await engine.dispose()


app = FastAPI(
    title="Support Tickets API",
    description="AI-powered система обработки обращений пользователей. "
                "Классификация и роутинг через Llama 3.3 70B (Groq).",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(users_router, prefix="/api/v1")


@app.get("/healthcheck", tags=["system"])
async def healthcheck():
    return {"status": "ok"}
