"""
Роутер диалогов (conversations).

Эндпоинты:
  POST /api/v1/conversations/
      — создать новый диалог. Привязывается к текущему пользователю из JWT.

  GET  /api/v1/conversations/
      — список диалогов текущего пользователя.

  POST /api/v1/conversations/{id}/messages
      — добавить сообщение в диалог. Принимает текст, возвращает
        сообщение пользователя + ответ AI.

  GET  /api/v1/conversations/{id}/messages
      — получить всю историю сообщений диалога.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User

router = APIRouter(prefix="/conversations", tags=["conversations"])


# ── Схемы запросов/ответов (определены здесь чтобы не плодить файлы) ──────────

class ConversationRead(BaseModel):
    """Данные диалога в ответе."""
    id: int
    user_id: int
    status: str

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """Тело запроса при отправке сообщения."""
    content: str


class MessageRead(BaseModel):
    """Данные одного сообщения в ответе."""
    id: int
    conversation_id: int
    role: str       # "user" или "ai"
    content: str

    class Config:
        from_attributes = True


# ── POST /conversations/ — создать диалог ─────────────────────────────────────

@router.post(
    "/",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Начать новый диалог",
    description="Создаёт новый диалог для авторизованного пользователя. "
                "user_id берётся из JWT токена автоматически.",
)
async def create_conversation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = Conversation(
        user_id=current_user.id,
        status="active",
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


# ── GET /conversations/ — список диалогов текущего пользователя ───────────────

@router.get(
    "/",
    response_model=list[ConversationRead],
    summary="Список диалогов пользователя",
    description="Возвращает все диалоги авторизованного пользователя.",
)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    return result.scalars().all()


# ── POST /conversations/{id}/messages — добавить сообщение ────────────────────

@router.post(
    "/{conversation_id}/messages",
    response_model=list[MessageRead],
    status_code=status.HTTP_201_CREATED,
    summary="Отправить сообщение в диалог",
    description="Добавляет сообщение пользователя и получает ответ от AI. "
                "Возвращает оба сообщения: от пользователя и от AI.",
)
async def add_message(
    conversation_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Проверяем что диалог существует и принадлежит текущему пользователю
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Диалог не найден",
        )
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому диалогу",
        )

    # Сохраняем сообщение пользователя
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=payload.content,
    )
    db.add(user_message)
    await db.flush()
    await db.refresh(user_message)

    # Получаем ответ от AI (через ai_service)
    # Если AI недоступен — возвращаем заглушку, диалог не прерывается
    ai_answer = await _get_ai_answer(conversation_id, payload.content)

    # Сохраняем ответ AI
    ai_message = Message(
        conversation_id=conversation_id,
        role="ai",
        content=ai_answer,
    )
    db.add(ai_message)
    await db.flush()
    await db.refresh(ai_message)

    return [user_message, ai_message]


# ── GET /conversations/{id}/messages — история сообщений ──────────────────────

@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageRead],
    summary="История сообщений диалога",
    description="Возвращает все сообщения диалога в хронологическом порядке.",
)
async def get_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Проверяем доступ
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Диалог не найден",
        )
    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому диалогу",
        )

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return result.scalars().all()


# ── Внутренняя функция: вызов AI ──────────────────────────────────────────────

async def _get_ai_answer(conversation_id: int, message: str) -> str:
    """
    Запрашивает ответ у AI Service.
    Если сервис недоступен — возвращает заглушку чтобы не ломать диалог.
    """
    import httpx
    from app.config import get_settings

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.AI_SERVICE_URL}/ai/answer",
                json={
                    "conversation_id": conversation_id,
                    "message": message,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("answer", "Не удалось получить ответ от AI.")
    except Exception:
        return "[AI Service временно недоступен. Ваше сообщение сохранено, агент ответит вручную.]"
