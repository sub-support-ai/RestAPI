from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)


class UserCreate(UserBase):
    # min_length=6 — разумный минимум для UX.
    # max_length=256 — потолок против DoS-обжора (мегабайтный "пароль"
    # заставил бы SHA-256 молоть впустую и забил бы JSON-парсер).
    # Ограничения bcrypt в 72 байта здесь НЕ валидируем: security.py
    # пропускает пароль через SHA-256 → hex (64 ASCII байта) перед bcrypt,
    # поэтому длинные и не-ASCII пароли работают корректно.
    password: str = Field(min_length=6, max_length=256)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
