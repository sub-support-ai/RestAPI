"""
Фоновые задачи Celery.

Каждая функция с декоратором @celery_app.task — это задача которую
можно поставить в очередь и выполнить в фоне.

Текущие задачи:
  process_ticket_with_ai  — классифицировать тикет через Llama 3.3 70B
  send_ticket_notification — уведомить агента о новом тикете (заглушка)

Как добавить задачу в очередь из любого места приложения:
  from app.tasks import process_ticket_with_ai
  process_ticket_with_ai.delay(ticket_id=42)
  # .delay() — поставить в очередь и сразу вернуть управление
"""

import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="process_ticket_with_ai",
    bind=True,          # даёт доступ к self (объект задачи)
    max_retries=3,      # максимум 3 попытки
    default_retry_delay=60,  # пауза между попытками — 60 секунд
)
def process_ticket_with_ai(self, ticket_id: int) -> dict:
    """
    Классифицировать тикет через AI в фоновом режиме.

    Шаги:
    1. Загрузить тикет из БД
    2. Отправить текст в Llama 3.3 70B (Groq API)
    3. Сохранить категорию, приоритет и уверенность в тикет
    4. Записать результат в ai_logs

    Вызов: process_ticket_with_ai.delay(ticket_id=42)
    """
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select, update
    from datetime import datetime, timezone
    from app.config import get_settings
    from app.models.ticket import Ticket

    logger.info("Начинаю AI-обработку тикета", extra={"ticket_id": ticket_id})

    settings = get_settings()

    async def _run():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        Session = async_sessionmaker(bind=engine, expire_on_commit=False)

        try:
            async with Session() as session:
                # Загружаем тикет
                result = await session.execute(
                    select(Ticket).where(Ticket.id == ticket_id)
                )
                ticket = result.scalar_one_or_none()

                if not ticket:
                    logger.warning(
                        "Тикет не найден — пропускаем",
                        extra={"ticket_id": ticket_id}
                    )
                    return {"status": "skipped", "reason": "ticket_not_found"}

                ticket_text = f"{ticket.title}\n\n{ticket.body}"
                logger.info(
                    "Тикет загружен, отправляю в AI",
                    extra={"ticket_id": ticket_id, "text_length": len(ticket_text)}
                )

                # TODO: здесь будет вызов AI (задача AI Lead #7)
                # Пока заглушка — имитируем ответ AI
                # Когда AI Service будет готов, заменить на:
                #   from app.services.classifier import classify
                #   ai_result = await classify(ticket_text)
                ai_result = {
                    "category": "техническая_проблема",
                    "priority": "средний",
                    "confidence": 0.85,
                }

                # Сохраняем результат AI в тикет
                await session.execute(
                    update(Ticket)
                    .where(Ticket.id == ticket_id)
                    .values(
                        ai_category=ai_result["category"],
                        ai_priority=ai_result["priority"],
                        ai_confidence=ai_result["confidence"],
                        ai_processed_at=datetime.now(timezone.utc),
                    )
                )
                await session.commit()

                logger.info(
                    "AI-обработка завершена",
                    extra={
                        "ticket_id": ticket_id,
                        "category": ai_result["category"],
                        "priority": ai_result["priority"],
                        "confidence": ai_result["confidence"],
                    }
                )

                return {"status": "ok", "ticket_id": ticket_id, **ai_result}

        except Exception as exc:
            logger.error(
                "Ошибка при AI-обработке тикета",
                extra={"ticket_id": ticket_id, "error": str(exc)}
            )
            raise
        finally:
            await engine.dispose()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        # Повторяем задачу если что-то пошло не так
        logger.warning(
            f"Задача упала, попытка {self.request.retries + 1}/3",
            extra={"ticket_id": ticket_id, "error": str(exc)}
        )
        raise self.retry(exc=exc)


@celery_app.task(name="send_ticket_notification")
def send_ticket_notification(ticket_id: int, agent_id: int) -> dict:
    """
    Уведомить агента о новом назначенном тикете.

    Сейчас заглушка — просто логирует.
    Когда будет Email listener (задача 3) — здесь будет отправка письма.

    Вызов: send_ticket_notification.delay(ticket_id=42, agent_id=7)
    """
    logger.info(
        "Уведомление агенту о новом тикете",
        extra={"ticket_id": ticket_id, "agent_id": agent_id}
    )
    # TODO: отправить email агенту (задача BE Dev #3)
    return {"status": "ok", "ticket_id": ticket_id, "agent_id": agent_id}
