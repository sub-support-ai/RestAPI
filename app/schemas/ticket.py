from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ticket(Base):
    """
    Обращение пользователя — центральная таблица системы.

    Жизненный цикл статуса:
      new → ai_processing → pending_agent → in_progress → resolved → closed

    AI-поля заполняются автоматически после вызова Llama 3.3 70B (Groq):
      ai_category     — категория тикета ("billing", "technical", "account", ...)
      ai_priority     — приоритет от модели (1=низкий, 5=критический)
      ai_confidence   — уверенность модели (0.0–1.0)
                        если < 0.7 → направляем к старшему агенту
      ai_processed_at — время обработки моделью (метрика скорости пайплайна)
    """
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # nullable=True — агент назначается после AI-классификации, не сразу
    agent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="new", nullable=False, index=True)

    # Приоритет выставленный пользователем (1–5)
    user_priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # ── AI-поля (Llama 3.3 70B через Groq) ────────────────────────────────────
    ai_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_priority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # ──────────────────────────────────────────────────────────────────────────

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="tickets")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="tickets")
    responses: Mapped[list["Response"]] = relationship("Response", back_populates="ticket")
    logs: Mapped[list["AILog"]] = relationship("AILog", back_populates="ticket")
