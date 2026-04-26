# Changelog

Все значимые изменения этого репозитория документируются здесь.
Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование: [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Added — критические фиксы AI-интеграции (R1–R4)

- **R1. Контракт `/ai/answer` — история сообщений вместо одной строки.**
  `app/routers/conversations.py::_get_ai_answer` теперь шлёт в AI-Lead
  `messages: list[{role, content}]` (последние 20 сообщений диалога) —
  модель видит контекст всего разговора, а не только последний вопрос.
  Внутренние роли мапятся: `"ai" → "assistant"` (стандарт OpenAI/Ollama).
  Ограничение в 20 сообщений защищает от разрастания prompt'а на длинных
  диалогах. AI-Lead уже принимал такой формат — на нём построены
  его смоук-тесты (`tests/test_answerer_http.py`), просто RestAPI этим
  не пользовался.

- **R2. Полный парсинг ответа AI: sources, confidence, escalate, model_version.**
  AI-Lead отдавал `{answer, confidence, escalate, sources, model_version}`,
  RestAPI читал только `answer`. Теперь все поля доходят до клиента
  через расширенный `MessageRead`:
  - `sources: list[{title, url}]` — источники RAG для UI-цитирования;
  - `ai_confidence`, `ai_escalate` — для офлайн-аудита решений модели;
  - `requires_escalation` — итоговый флаг "красной зоны" (см. R3).

  В БД на `messages` добавлены 4 nullable-колонки: `ai_confidence`,
  `ai_escalate`, `sources` (JSON), `requires_escalation`. Миграция
  `b2c4e6f8a0d2_add_ai_metadata_to_messages.py` написана вручную через
  `op.batch_alter_table` — совместимо с SQLite (для тестов) и Postgres.

- **R3. Красная зона `confidence < 0.6` → форс-эскалация.**
  Если модель вернула низкую уверенность (порог в `RED_ZONE_THRESHOLD = 0.6`,
  как требует план проекта) ИЛИ сама выставила `escalate=True` — на
  AI-сообщении ставится `requires_escalation = True`. Клиент по этому
  флагу обязан НЕ показывать ответ как окончательный, а предложить
  пользователю 1-click эскалацию через `POST /escalate` (см. R4).
  Важно: это НЕ та же 0.8, что в `app/services/routing.py` — там порог
  про выбор агента (свободный vs старший), а 0.6 — про "показывать ли
  draft пользователю вообще".

- **R4. 1-click автоматическое заполнение тикета: `POST /conversations/{id}/escalate`.**
  Новый эндпоинт собирает из истории диалога title (первое сообщение
  пользователя), body (вся история ролями), извлекает `steps_tried`
  по эвристике на ключевые фразы ("пробовал", "перезагружал" и т.п.),
  вызывает классификатор AI-Lead для category/priority/department,
  создаёт `Ticket(status="pending_user", confirmed_by_user=False,
  ticket_source="ai_generated", conversation_id=...)`, назначает агента
  и переводит `Conversation.status="escalated"`. Пользователь видит
  pre-filled форму — один клик "Отправить" подтверждает тикет.

- **AILog при эскалации.** В `escalate_conversation` пишется AILog с
  `outcome="escalated_ai_ticket"` — закрывает Y9 (раньше outcome
  никогда не выставлялся). Логи привязаны и к ticket_id, и к
  conversation_id — полная трассировка решений модели для дообучения.

### Added — новые тесты

- `tests/test_conversations.py` — 9 тестов на:
  - fallback `_get_ai_answer` (AI Service недоступен → red zone);
  - сохранение истории в хронологическом порядке;
  - 404 на чужой диалог при POST /messages и POST /escalate;
  - happy-path /escalate: создание тикета + перевод conversation в escalated;
  - 400 на пустой диалог при /escalate;
  - `_load_history_for_ai`: маппинг ролей user→user, ai→assistant, лимит истории;
  - `_extract_steps_tried`: эвристика по ключевым словам, фильтр по role.

### Changed

- **O5. `model_version="unknown"` литерал убран.**
  `app/routers/tickets.py::create_ticket` и
  `app/routers/conversations.py::escalate_conversation` теперь падают на
  `settings.AI_MODEL_VERSION_FALLBACK` из `.env`, если AI Service не
  вернул model_version. Литерал `"unknown"` отравлял датасет: разные
  версии модели сваливались в одну "unknown"-корзину, метрики качества
  по версиям не считались. Дефолтное значение — `"mistral-unspecified"`,
  переопределяется через переменную окружения `AI_MODEL_VERSION_FALLBACK`.

- **`app/models/message.py`**: добавлены поля `ai_confidence`, `ai_escalate`,
  `sources`, `requires_escalation` (все nullable). Существующие user-сообщения
  и AI-сообщения, созданные до миграции, остаются с NULL — UI просто не
  показывает источники.

- **`app/routers/conversations.py::_load_history_for_ai`**: вторичная
  сортировка по `Message.id.desc()` рядом с `created_at.desc()`. В одной
  транзакции `created_at` одинаковый (server_default=func.now() возвращает
  время начала транзакции), без вторичного ключа порядок был
  недетерминированным — тест `test_load_history_maps_roles_and_limits_length`
  это поймал.

### Notes

- На стороне AI-Lead контракт уже соответствовал: 43 теста в
  `tests/test_answerer_http.py` и `tests/test_classifier_http.py` фиксируют
  формат. RestAPI был отстающей стороной — сейчас разрыв закрыт.
- НЕ сделано в этом релизе (вынесено в отдельные задачи):
  - O6: Agent роль не видит назначенные тикеты в `list_tickets`;
  - O7: rate limiting на `POST /tickets` и `POST /messages`;
  - Y10: переход `Conversation.status="resolved"` при положительном фидбэке
    пользователя (сейчас "active" → "escalated" работает, "active" →
    "resolved" нет).

## [0.2.0] — 2026-04-19

### Security

- Fail-fast на дефолтном `JWT_SECRET_KEY` в production (`app/config.py`).
- Bcrypt 72-byte truncation guard, rate limit на `/auth/*`, audit log на
  важные события (login/register/ticket.create/delete/role.change).
- `/stats` и `/users` закрыты авторизацией.

### Added

- AILog.ai_response_time_ms — метрика "1,01 сек" из питч-дека считается
  по реальным данным.
- Audit log без FK на удаляемых юзеров — действия удалённого пользователя
  остаются в журнале.

[Unreleased]: https://github.com/sub-support-ai/RestAPI/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sub-support-ai/RestAPI/releases/tag/v0.2.0
