from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    """
    Одно сообщение в диалоге между пользователем и AI.

    role = "user" — сообщение от пользователя
    role = "ai"   — ответ от AI-ассистента

    Все сообщения одного диалога связаны через conversation_id.
    Когда нужно создать тикет — AI берёт все сообщения диалога
    и формирует из них описание проблемы автоматически.
    """
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # "user" или "ai"
    role: Mapped[str] = mapped_column(String(10), nullable=False)

    # Текст сообщения
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Связь с диалогом
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
