import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketRead, TicketStatusUpdate
from app.services.ai_classifier import classify_ticket


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("/", response_model=list[TicketRead])
async def list_tickets(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    department: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """Список тикетов. Можно фильтровать по отделу и статусу."""
    query = select(Ticket).offset(skip).limit(limit)

    if department:
        query = query.where(Ticket.department == department)
    if status_filter:
        query = query.where(Ticket.status == status_filter)

    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    """Один тикет по id."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return ticket

@router.post("/", response_model=TicketRead, status_code = status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreate, db: AsyncSession = Depends(get_db)):
    """
    Создать тикет. После создания — отправляем в AI на классификацию.
    AI определяет категорию, приоритет и генерирует черновик ответа.
    """
    logger.info("Создание тикета", extra={"user_id": payload.user_id})

    # Шаг 1 — сохраняем тикет в базу со статусом ai_processing
    ticket = Ticket(
        title=payload.title,
        body=payload.body,
        user_id=payload.user_id,
        user_priority=payload.user_priority,
        ticket_source="user_written",
        status="ai_processing",
    )
    db.add(ticket)
    await db.flush() # получаем id от базы

    # Шаг 2 — отправляем в AI на классификацию
    # Если AI Service недоступен — classify_ticket вернёт заглушку
    ai_result = await classify_ticket(ticket.id, ticket.title, ticket.body)

    # Шаг 3 — записываем результат AI в тикет
    ticket.ai_category = ai_result.get("category")
    ticket.ai_priority = ai_result.get("priority")
    ticket.ai_confidence = ai_result.get("confidence")
    ticket.ai_processed_at = datetime.now()
    ticket.status = "pending_user" # ждём подтверждения от пользователя

    logger.info(
        "Тикет Классифицирован",
        extra={
            "ticket_id": ticket.id,
            "category": ticket.ai_category,
            "confidence": ticket.ai_confidence,
        }
    )

    # flush до refresh: иначе AsyncSession подтянет из БД старую строку (ai_processing).
    await db.flush()
    await db.refresh(ticket)
    return ticket

@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновить статус тикета."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Ticket not found",
        )
    ticket.status = payload.status

    # Если тикет подтверждён пользователем — помечаем
    if payload.status == "confirmed":
        ticket.confirmed_by_user = True

    # Если тикет закрыт — записываем время
    if payload.status in ("resolved", "closed"):
        ticket.resolved_at = datetime.now()

    logger.info(
        "Статус тикета обновлён",
        extra={"ticket_id": ticket_id, "new_status": payload.status}
    )

    await db.flush()
    await db.refresh(ticket)
    return ticket

@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удалить тикет.
    TODO задача 5: защитить ролью admin через JWT.
    """
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    db.delete(ticket)
    logger.info("Тикет удалён", extra={"ticket_id": ticket_id})
