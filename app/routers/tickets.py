from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketRead, TicketStatusUpdate

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ── Вспомогательная функция: найти свободного агента ──────────────────────────
async def find_available_agent(db: AsyncSession, department: str) -> Agent | None:
    """
    Ищет агента в нужном отделе с наименьшим числом активных тикетов.
    Это и есть механика перехвата — самый свободный агент получает тикет.
    """
    result = await db.execute(
        select(Agent)
        .where(Agent.department == department)   # только нужный отдел
        .where(Agent.is_active == True)          # только активные агенты
        .order_by(Agent.active_ticket_count)     # сортируем: у кого меньше тикетов — первый
        .limit(1)                                # берём одного — самого свободного
    )
    return result.scalar_one_or_none()


# ── POST /tickets/ — создать тикет ────────────────────────────────────────────
@router.post("/", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(payload: TicketCreate, db: AsyncSession = Depends(get_db)):
    from app.services.ai_classifier import classify_ticket

    ai_result = await classify_ticket(
        ticket_id=0,
        title=payload.title,
        body=payload.body,
    )

    # Определяем отдел из AI классификации
    department = payload.department if hasattr(payload, "department") else "IT"

    # Ищем свободного агента сразу при создании
    agent = await find_available_agent(db, department)

    ticket = Ticket(
        user_id=payload.user_id,
        title=payload.title,
        body=payload.body,
        user_priority=payload.user_priority,
        department=department,
        agent_id=agent.id if agent else None,    # назначаем агента если нашли
        ai_category=ai_result.get("category"),
        ai_priority=ai_result.get("priority"),
        ai_confidence=ai_result.get("confidence"),
        ai_processed_at=datetime.now(timezone.utc),
    )
    db.add(ticket)
    await db.flush()

    # Если агент найден — увеличиваем его счётчик на 1
    if agent:
        agent.active_ticket_count += 1

    await db.refresh(ticket)
    return ticket


# ── GET /tickets/ — список тикетов ────────────────────────────────────────────
@router.get("/", response_model=list[TicketRead])
async def list_tickets(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).offset(skip).limit(limit))
    return result.scalars().all()


# ── GET /tickets/{id} — один тикет ────────────────────────────────────────────
@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


# ── PATCH /tickets/{id} — изменить статус ─────────────────────────────────────
@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = payload.status

    # Если тикет закрывается или решается — уменьшаем счётчик агента на 1
    closing_statuses = {"resolved", "closed"}
    if payload.status in closing_statuses and old_status not in closing_statuses:
        if ticket.agent_id:
            agent_result = await db.execute(
                select(Agent).where(Agent.id == ticket.agent_id)
            )
            agent = agent_result.scalar_one_or_none()
            if agent and agent.active_ticket_count > 0:
                agent.active_ticket_count -= 1  # -1 при закрытии

        ticket.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(ticket)
    return ticket


# ── DELETE /tickets/{id} — удалить тикет ──────────────────────────────────────
@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Если тикет был активен — уменьшаем счётчик агента
    if ticket.agent_id and ticket.status not in {"resolved", "closed"}:
        agent_result = await db.execute(
            select(Agent).where(Agent.id == ticket.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent and agent.active_ticket_count > 0:
            agent.active_ticket_count -= 1

    db.delete(ticket)
    await db.flush()
