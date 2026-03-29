# Support Tickets AI — Project Context

## Tech Stack
- **Backend**: FastAPI + PostgreSQL + SQLAlchemy async
- **AI Service**: Mistral AI (recently switched from Llama 3.3 70B)
- **Testing**: Pytest
- **Infrastructure**: Docker
- **GitHub**: github.com/sub-support-ai/MainFastAPI
- **AI Lead Repo**: github.com/sub-support-ai/AI-Lead

## Key Architectural Decisions
1. **Direct async HTTP calls** to AI Service (no Celery/Redis due to low latency)
2. **Text-based priorities** (stored as String(20), not enum)
3. **`declined` status** for rejected AI tickets
4. **Concatenation responsibility**: BE concatenates `title + body` → `ticket_text` for AI Service

## Recent Changes
- **Model Migration**: Switched from Llama 3.3 70B to Mistral
- **Integration**: Check AI-Lead repo for exact Mistral model version and API contract
- **Response Format**: AI Service still returns JSON with `priority`, `category`, `action` fields
- **Error Handling**: Maintained same fallback patterns in `ai_classifier.py`

## Database Schema (7 tables)
- Users, Tickets, AI Classifications, Status History, etc.
- Uses SQLAlchemy 2 async ORM

## Current Endpoints (tickets.py)
- `POST /tickets/` — Create ticket
- `GET /tickets/` — List tickets (with filters)
- `GET /tickets/{id}` — Get single ticket
- `PATCH /tickets/{id}` — Update ticket
- `DELETE /tickets/{id}` — Delete ticket

## Team Structure
- **AI Lead**: Mistral integration, provides `ticket_text` field (title + body)
- **AI Dev**: RAG pipeline implementation
- **BE Dev 1 (YOU)**: JWT authentication, main architectural lead
- **BE Dev 2**: Routing logic, resolve endpoint
- **Frontend 1**: Chat interface
- **Frontend 2**: Agent/dashboard interface

## Critical SQLAlchemy Patterns
```python
# ✅ Correct
db.delete(model_instance)  # sync, not await
db.flush()  # MUST flush before refresh
db.refresh(model_instance)

# ❌ Wrong
await db.delete(model_instance)  # SQLAlchemy 2 uses sync delete
db.refresh() before flush  # causes stale reads
```

## Test Execution
```powershell
py -m pytest -q              # Quick test run
py -m pytest -v              # Verbose output
py -m pytest tests/test_tickets.py  # Specific test file
```

## Environment Variables (.env)
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/support_tickets_ai
MISTRAL_API_KEY=<your_mistral_key>
MISTRAL_MODEL=<check_AI-Lead_repo>
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

## API Contract with AI Service
**Request to Mistral (via AI Lead):**
- Input: `ticket_text` (concatenated title + body)
- Expected response: JSON with `priority`, `category`, `action`

**Response handling in `ai_classifier.py`:**
- Parse JSON response
- Validate against schema
- Return (priority, category, action) tuple
- Handle exceptions → return fallback classification

## Integration Points
1. **Chat Frontend** → User query → Backend `/tickets/` endpoint
2. **Backend** → Concatenates title + body → Calls AI Service
3. **AI Service (Mistral)** → Returns classification
4. **Backend** → Creates/declines ticket based on classification
5. **Agent Dashboard** → Shows tickets, allows manual override

## Known Limitations & Workarounds
- Mistral latency may vary vs Llama → monitor response times
- Text priorities as strings require consistent formatting across API
- No Celery/Redis = synchronous ticket processing (acceptable for current load)

## Before Starting New Work
1. Read latest commit history in MainFastAPI repo
2. Check AI-Lead repo for Mistral model details and API changes
3. Verify `.env` has correct MISTRAL_API_KEY
4. Run test suite: `py -m pytest -q` to confirm baseline
5. Check for any pending PRs from AI Lead or Frontend teams

## Debugging Tools
- **DBeaver**: Direct DB inspection of `support_tickets_ai` database
- **Pytest**: Run tests incrementally, check coverage
- **FastAPI Docs**: `http://localhost:8000/docs` (if running locally)
- **Groq/Mistral Playground**: Test prompts before integration

## Communication Patterns
- **AI Lead**: Direct message about response format changes
- **AI Dev**: Coordinate on RAG pipeline updates
- **BE Dev 2**: Align on routing logic changes
- **Frontend teams**: Confirm API contracts before releasing

## Project Status
- ✅ Stack initialized, DB schema locked in
- ✅ 8 tests passing
- ✅ 5 core endpoints working
- 🔄 **IN PROGRESS**: Mistral integration (verify in AI-Lead repo)
- ⏳ Integration tests with AI Service
- ⏳ Accelerator presentation prep

---

**Last Updated**: March 29, 2026  
**AI Model**: Mistral (check AI-Lead for exact version)  
**Backend Lead**: Daya
