# MainFastAPI — Support Tickets API

FastAPI‑сервис для обработки обращений пользователей (тикеты) с Postgres (в Docker) и асинхронным SQLAlchemy.

## Быстрый старт (Docker)

1) Создайте файл `.env` на основе примера:

```bash
copy .env.example .env
```

2) Поднимите Postgres и приложение:

```bash
docker compose up --build
```

После старта:
- `GET /healthcheck` → `{"status":"ok"}`
- Swagger UI: `http://localhost:8000/docs`

## Быстрый старт (локально на Windows)

Важно: у вас Python запускается через `py` (а `python` может быть не в PATH).

1) Установите зависимости:

```bash
py -m pip install -r requirements-dev.txt
```

2) Создайте `.env`:

```bash
copy .env.example .env
```

3) Запустите Postgres (рекомендуется через Docker):

```bash
docker compose up -d db
```

4) Запустите API:

```bash
py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Тесты

По умолчанию тесты используют SQLite (async) и не требуют Postgres:

```bash
py -m pytest -q
```

Если хотите прогонять тесты на Postgres, задайте переменную окружения `TEST_DATABASE_URL`:

```bash
set TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_db
py -m pytest -q
```

## Переменные окружения

Смотрите `.env.example`:
- `POSTGRES_HOST=db` — для запуска в Docker Compose (приложение обращается к сервису `db`)
- `GROQ_API_KEY` — ключ Groq (если будете подключать AI‑часть)

