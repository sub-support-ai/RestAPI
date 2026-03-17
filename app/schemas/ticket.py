from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    user_priority: int = Field(default=3, ge=1, le=5)


class TicketCreate(TicketBase):
    user_id: int


class TicketRead(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    agent_id: int | None = None
    status: str

    ai_category: str | None = None
    ai_priority: int | None = None
    ai_confidence: float | None = None
    ai_processed_at: datetime | None = None

    created_at: datetime
    updated_at: datetime | None = None
    resolved_at: datetime | None = None
