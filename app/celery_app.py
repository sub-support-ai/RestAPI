"""
Настройка Celery — системы фоновых задач.

Как это работает:
1. Приходит тикет → приложение кладёт задачу в очередь Redis → сразу отвечает "принято"
2. Celery worker (отдельный процесс) берёт задачу из Redis и обрабатывает её
3. AI классифицирует тикет, результат сохраняется в БД

Зачем это нужно:
- Пользователь не ждёт пока AI думает (2-5 секунд)
- Если AI упал — задача останется в очереди и выполнится позже
- Можно запустить несколько workers параллельно под нагрузку
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Создаём приложение Celery
# broker — куда класть задачи (Redis)
# backend — куда сохранять результаты выполненных задач (тоже Redis)
celery_app = Celery(
    "support_tickets",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],  # файл где лежат задачи
)

celery_app.conf.update(
    # Формат сообщений
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Часовой пояс
    timezone="UTC",
    enable_utc=True,

    # Если задача упала — попробовать ещё 3 раза с паузой 60 секунд
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Результаты хранить 1 час (потом удаляются из Redis автоматически)
    result_expires=3600,

    # Не брать больше одной задачи за раз — надёжнее при сбоях
    worker_prefetch_multiplier=1,
)
