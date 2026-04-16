"""
Роутер тикетов — финальная версия с:
  - JWT защитой на все эндпоинты
  - Роутингом через app/services/routing.py (assign_agent / unassign_agent)
  - Логикой confidence < 0.8 → старший агент (внутри assign_agent)
  - Эндпоинтом PATCH /tickets/{id}/resolve — агент закрывает тикет
  - Записью feedback в ai_logs при resolve
  - Фильтром по department для Frontend 2
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.ai_log import AILog
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketRead, TicketStatusUpdate
from app.services.routing import assign_agent, unassign_agent

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ── Схема для resolve ─────────────────────────────────────────────────────────

class ResolvePayload(BaseModel):
    """
    Тело запроса при закрытии тикета агентом.

    agent_accepted_ai_response:
        True  — агент согласился с черновиком AI и отправил его как есть
        False — агент написал свой ответ
    correction_lag_seconds:
        Сколько секунд прошло между созданием тикета и закрытием.
        Нужно для метрик скорости работы.
    """
    agent_accepted_ai_response: bool
    correction_lag_seconds: int | None = None


# ── POST /tickets/ ─────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=TicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать тикет",
    description="Создаёт тикет, вызывает AI классификацию и назначает агента. "
                "Если AI уверен < 0.8 — назначается старший агент для проверки.",
)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.ai_classifier import classify_ticket

    ai_result = await classify_ticket(
        ticket_id=0,
        title=payload.title,
        body=payload.body,
    )

    # Приоритет: явное поле от пользователя > ответ AI > "IT" по умолчанию
    department = payload.department or ai_result.get("department") or "IT"

    ticket = Ticket(
        user_id=payload.user_id,
        title=payload.title,
        body=payload.body,
        user_priority=payload.user_priority,
        department=department,
        ai_category=ai_result.get("category"),
        ai_priority=ai_result.get("priority"),
        ai_confidence=ai_result.get("confidence"),
        ai_processed_at=datetime.now(timezone.utc),
    )
    db.add(ticket)
    await db.flush()

    await assign_agent(db, ticket)
    # flush до refresh — иначе SELECT из refresh() затрёт agent_id в памяти
    await db.flush()

    # Пишем AILog при создании — время ответа AI попадает в метрики
    # "1,01 сек" из питч-дека (ai_response_time_ms).
    db.add(AILog(
        ticket_id=ticket.id,
        model_version=ai_result.get("model_version", "unknown"),
        predicted_category=ai_result.get("category") or "неизвестно",
        predicted_priority=ai_result.get("priority") or "средний",
        confidence_score=float(ai_result.get("confidence") or 0.0),
        routed_to_agent_id=ticket.agent_id,
        ai_response_draft=ai_result.get("draft_response"),
        ai_response_time_ms=ai_result.get("response_time_ms"),
    ))

    await db.refresh(ticket)
    return ticket


# ── GET /tickets/ ──────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[TicketRead],
    summary="Список тикетов",
    description="Возвращает тикеты с пагинацией. "
                "Фильтр department: IT, HR, finance.",
)
async def list_tickets(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    department: str | None = Query(default=None, description="Фильтр по отделу: IT, HR, finance"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Ticket)
    if department:
        query = query.where(Ticket.department == department)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


# ── GET /tickets/{id} ──────────────────────────────────────────────────────────

@router.get(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Получить тикет по ID",
)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


# ── PATCH /tickets/{id} — обновить статус ─────────────────────────────────────

@router.patch(
    "/{ticket_id}",
    response_model=TicketRead,
    summary="Обновить статус тикета",
)
async def update_ticket_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = payload.status

    closing_statuses = {"resolved", "closed"}
    if payload.status in closing_statuses and old_status not in closing_statuses:
        await unassign_agent(db, ticket)
        ticket.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(ticket)
    return ticket


# ── PATCH /tickets/{id}/resolve — агент закрывает тикет ───────────────────────

@router.patch(
    "/{ticket_id}/resolve",
    response_model=TicketRead,
    summary="Закрыть тикет (агент)",
    description=(
        "Агент принимает решение по тикету. Статус → closed, resolved_at = now(). "
        "Записывает в ai_logs: принял ли агент черновик AI и за сколько секунд."
    ),
)
async def resolve_ticket(
    ticket_id: int,
    payload: ResolvePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = "closed"
    ticket.resolved_at = datetime.now(timezone.utc)
    ticket.confirmed_by_user = True

    if old_status not in {"resolved", "closed"}:
        await unassign_agent(db, ticket)

    # Записываем или обновляем ai_log
    log_result = await db.execute(
        select(AILog)
        .where(AILog.ticket_id == ticket_id)
        .order_by(AILog.created_at.desc())
        .limit(1)
    )
    ai_log = log_result.scalar_one_or_none()

    if ai_log:
        ai_log.agent_accepted_ai_response = payload.agent_accepted_ai_response
        ai_log.routing_was_correct = True
        ai_log.reviewed_at = datetime.now(timezone.utc)
        if payload.correction_lag_seconds is not None:
            ai_log.correction_lag_seconds = payload.correction_lag_seconds
    else:
        ai_log = AILog(
            ticket_id=ticket_id,
            model_version="manual",
            predicted_category=ticket.ai_category or "неизвестно",
            predicted_priority=ticket.ai_priority or "средний",
            confidence_score=ticket.ai_confidence or 0.0,
            agent_accepted_ai_response=payload.agent_accepted_ai_response,
            routing_was_correct=True,
            reviewed_at=datetime.now(timezone.utc),
            correction_lag_seconds=payload.correction_lag_seconds,
        )
        db.add(ai_log)

    await db.flush()
    await db.refresh(ticket)
    return ticket


# ── DELETE /tickets/{id} — только admin ───────────────────────────────────────

@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить тикет",
    description="Доступно только администраторам (role=admin).",
)
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    if ticket.status not in {"resolved", "closed"}:
        await unassign_agent(db, ticket)

    await db.delete(ticket)
    await db.flush()
