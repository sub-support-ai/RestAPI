"""Запись событий в audit_log.

Конвенция: вызов log_event() — это часть ТОЙ ЖЕ транзакции, что и
основное действие. Пример:
    - DELETE /tickets/42:
        1) db.delete(ticket)
        2) await log_event(db, action="ticket.delete", ...)
        3) db.commit()  ← оба изменения попадают в БД одной транзакцией

Если шаг 3 упадёт — оба отката. Инвариант: если в audit_log есть запись
о ticket.delete, значит тикет действительно был удалён (и наоборот).
Это сильнее, чем "логируем в файл перед удалением" — там возможен
рассинхрон (залогировали, а БД упала перед commit).
"""

import json
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def _client_ip(request: Optional[Request]) -> Optional[str]:
    """IP из request, если request передали. Некоторые вызовы могут
    логировать без request (например, фоновые задачи) — тогда IP=None."""
    if request is None or request.client is None:
        return None
    return request.client.host


async def log_event(
    db: AsyncSession,
    *,
    action: str,
    user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    request: Optional[Request] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    """Добавить событие в audit_log.

    ВАЖНО: функция НЕ делает commit — это ответственность вызывающего
    handler'а (см. docstring модуля). db.add() ставит объект в pending-очередь
    сессии, он уйдёт в БД вместе с остальными изменениями при db.commit().

    Все параметры после `db` — keyword-only (через `*`), чтобы случайно
    не перепутать порядок `action` и `user_id` в вызове.
    """
    entry = AuditLog(
        action=action,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        ip=_client_ip(request),
        details=json.dumps(details, ensure_ascii=False) if details else None,
    )
    db.add(entry)
    # Flush (но не commit): получаем id, ловим constraint-ошибки ДО
    # того как handler продолжит работу. Если флашить позже — ошибка
    # всплывёт из commit и придётся разбираться, какая именно модель
    # упала. При flush здесь — ошибка локальна этой строке.
    await db.flush()
