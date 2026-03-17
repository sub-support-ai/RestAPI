from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Agent(Base):
    """
    Агент поддержки — обрабатывает тикеты.

    Отделён от User намеренно: у агента есть специализация и метрики
    которые AI использует при роутинге.

    specialty         — тематика агента ("billing", "technical", "general").
                        Llama классифицирует тикет → AI ищет агента
                        с подходящей specialty.

    active_ticket_count — текущая нагрузка. AI не направляет тикеты
                          перегруженным агентам.

    ai_routing_score  — качество AI-роутинга на этого агента (0.0–1.0).
                        Считается из ai_logs: сколько раз агент соглашался
                        с решением модели. Растёт по мере дообучения.
    """
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False, default="general")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    active_ticket_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_routing_score: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="agent")
