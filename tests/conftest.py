import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.main import app

# Отдельная база для тестов — не трогает рабочие данные.
# По умолчанию используем SQLite, чтобы тесты проходили "из коробки"
# без поднятого Postgres. При необходимости можно переопределить через env:
#   TEST_DATABASE_URL=postgresql+asyncpg://...  (например, в CI)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///./test.db",
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Создаём все таблицы перед тестами, удаляем после."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Сессия с rollback после каждого теста — тесты изолированы."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """HTTP-клиент с подменой get_db на тестовую сессию."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
