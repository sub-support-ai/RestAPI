from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AILog(Base):
    """
    Журнал каждого решения Llama 3.3 70B. Три назначения:

    1. МЕТРИКИ ДЛЯ АКСЕЛЕРАТОРА
       Из этой таблицы считаем: accuracy классификации, % принятых
       черновиков, динамику точности по времени. Конкретные цифры
       для питч-дека и защиты.

    2. ДАТАСЕТ ДЛЯ ДООБУЧЕНИЯ
       Каждая строка с agent_corrected_category — обучающий пример:
       (текст тикета → правильная категория). AI lead использует
       эти строки для fine-tune следующей версии модели.

    3. ОБЪЯСНИМОСТЬ
       Можем показать комиссии: "вот что модель решила, вот почему,
       вот как агент это оценил."
    """
    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Решение модели ─────────────────────────────────────────────────────────
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_category: Mapped[str] = mapped_column(String(100), nullable=False)
    predicted_priority: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    routed_to_agent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    # Копия черновика — хранится здесь даже если Response удалят
    ai_response_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # ──────────────────────────────────────────────────────────────────────────

    # ── Обратная связь от агента ───────────────────────────────────────────────
    # Согласился ли агент с роутингом (None = ещё не проверено)
    routing_was_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Если агент изменил категорию — правильная категория здесь.
    # Это и есть датасет для fine-tune: predicted vs corrected.
    agent_corrected_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Принял ли агент AI-черновик без изменений.
    # Растущий % принятия = модель улучшается. Главная метрика для питч-дека.
    agent_accepted_ai_response: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Сколько секунд агент потратил на проверку AI-решения.
    # Падающее значение = агент всё больше доверяет модели.
    correction_lag_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # ──────────────────────────────────────────────────────────────────────────

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="logs")
    routed_to_agent: Mapped[Optional["Agent"]] = relationship("Agent")
