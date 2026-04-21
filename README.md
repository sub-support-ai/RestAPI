[![CI/CD](https://img.shields.io/badge/CI-passing-brightgreen?logo=githubactions)](Ссылка_на_ваш_экшен)
[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow?logo=opensourceinitiative)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
# Support Tickets API

FastAPI‑сервис для обработки обращений пользователей (тикеты) с Postgres (в Docker) и асинхронным SQLAlchemy.

## Структура:
```
app/
  routers/       HTTP endpoints
  models/        SQLAlchemy ORM
  schemas/       Pydantic DTOs
  services/      бизнес-логика (audit, rate_limit, …)
  main.py        app factory + middleware
alembic/         миграции БД
tests/           pytest
```

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
- `GET /healthcheck` → `{"status":"ok","database":"ok"}`
- Swagger UI: `http://localhost:8000/docs`

Миграции БД накатываются автоматически при старте контейнера
(`alembic upgrade head` в `docker-compose.yml`).

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

4) Накатите миграции БД:

```bash
py -m alembic upgrade head
```

5) Запустите API:

```bash
py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Миграции БД (Alembic)

Схема БД версионируется через Alembic. Список возможных команд:

```bash
# Применить все миграции до актуальной версии (всегда безопасно, идемпотентно)
py -m alembic upgrade head

# Посмотреть текущую версию БД
py -m alembic current

# История миграций
py -m alembic history

# Создать новую миграцию после изменения моделей
# (Alembic сравнит модели с текущей БД и сгенерит diff)
py -m alembic revision --autogenerate -m "добавил поле X в таблицу Y"

# ВАЖНО: прочитать сгенерированную миграцию перед коммитом.
# autogenerate не распознаёт переименования (воспринимает как drop+add,
# что потеряет данные) и может упустить изменения типов.

# Откатить одну миграцию назад
py -m alembic downgrade -1
```

Файлы миграций живут в `alembic/versions/` и коммитятся в git.

### Существующая БД (апгрейд с v0.1 → v0.2)

Если БД уже была развёрнута до того, как появился Alembic — таблицы уже
существуют, и `alembic upgrade head` упадёт с "relation already exists".
Нужно единожды "приклеить" текущее состояние к baseline-миграции:

```bash
py -m alembic stamp head
```

Эта команда записывает в `alembic_version` что база "уже на актуальной
версии", не выполняя сам upgrade. После этого все последующие миграции
пойдут обычным порядком.

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

