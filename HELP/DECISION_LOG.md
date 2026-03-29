# Support Tickets AI — Decisions Log

**Purpose**: Record architectural decisions, rationale, and what was considered+rejected. Prevents suggestion of already-decided patterns.

---

## ✅ Locked Decisions

### Decision 1: Direct HTTP Calls (No Celery/Redis)

**Date**: March 15, 2026  
**Decided by**: Daya (BE Lead) + AI Lead  
**Status**: ✅ LOCKED

**What**: Make synchronous HTTP calls from BE to AI Service (Groq then Mistral).  
**Why**:
- AI latency already ~2-3s per request
- Queue overhead (network + serialization) = not worth complexity
- FastAPI handles ~1000 concurrent connections easily
- Fallback classification handles AI Service outages
- Load for pilot: ~100 tickets/day (synchronous is fine)

**What was considered**:
- ❌ Celery + Redis: Added complexity, new failure modes, not needed at this load
- ❌ gRPC: Overkill for simple classify endpoint
- ✅ Chosen: Direct httpx async calls

**Tradeoff**: Timeout risk if AI Service slow (mitigated by 5s timeout + fallback).

**Trigger**: Do NOT suggest adding Celery/task queue unless load >10k tickets/day.

---

### Decision 2: Text-Based Priorities (Not SQL Enum)

**Date**: March 16, 2026  
**Decided by**: Daya (BE Lead) + AI Lead  
**Status**: ✅ LOCKED

**What**: Store priorities as `String(20)` in DB, validate on request.  
**Why**:
- AI Lead can experiment with priority labels without DB migrations
- Flexible for later: `"urgent-security"`, `"urgent-billing"`, etc.
- Validation is fast (<1ms)
- Easier to adjust based on user feedback

**What was considered**:
- ❌ PostgreSQL ENUM: Type-safe but locked schema to BE deployments
- ❌ JSON field: Overkill for simple string list
- ✅ Chosen: Text + CHECK constraint + validation

**Tradeoff**: Less type safety (mitigated by Pydantic validation).

**Trigger**: Do NOT suggest converting to SQL ENUM.

---

### Decision 3: One-Click Confirmation UI (Not Auto-Create)

**Date**: March 17, 2026  
**Decided by**: Daya (BE Lead) + Frontend 1  
**Status**: ✅ LOCKED

**What**: AI classifies ticket, user clicks "Confirm" button, then ticket is created.  
**Why**:
- AI accuracy is ~85% (hallucination risk)
- One misrouted ticket = 10 min agent debugging
- Confirmation = feedback loop for improving AI over time
- **This is the business model**: humans-in-the-loop, not full automation

**What was considered**:
- ❌ Auto-create: Faster but kills trust in system
- ❌ Batch confirmation: Overloads agents with 100 pending tickets
- ✅ Chosen: One-click per ticket

**Tradeoff**: Slower workflow (mitigated by fast frontend, preloading).

**Trigger**: Do NOT suggest auto-creation. Do NOT remove confirm button.

---

### Decision 4: Concatenation in BE (Not Frontend or AI Service)

**Date**: March 18, 2026  
**Decided by**: Daya (BE Lead) + AI Lead  
**Status**: ✅ LOCKED

**What**: Backend concatenates `title + body` into single `ticket_text` field.  
**Why**:
- AI Service gets single, clean input field (simpler contract)
- BE controls formatting consistency
- If formatting rules change, only BE code updates (not AI Service)
- Avoids "frontend developer accidentally adds emoji breaking AI parsing"

**What was considered**:
- ❌ Frontend concatenates: No control over format, inconsistency
- ❌ AI Service expects both: Doubles parameter surface area
- ✅ Chosen: BE concatenates with format `"{title}\n\n{body}"`

**Tradeoff**: BE owns responsibility for formatting.

**Trigger**: Do NOT move concatenation logic to frontend or AI Service.

---

### Decision 5: FastAPI + PostgreSQL + SQLAlchemy Async

**Date**: March 1, 2026  
**Decided by**: Daya (BE Lead) + Backend team lead  
**Status**: ✅ LOCKED

**What**: Full async stack for high concurrency.  
**Why**:
- Supports parallel AI requests without blocking
- PostgreSQL async driver (asyncpg) is battle-tested
- SQLAlchemy 2 async is stable
- Scales vertically well for pilot

**What was considered**:
- ❌ Django + Sync: More batteries included but slower for async I/O
- ❌ Flask: Lightweight but no async ORM
- ✅ Chosen: FastAPI + SQLAlchemy async

**Tradeoff**: More complex query patterns (flush/refresh requirements).

**Trigger**: Do NOT suggest sync framework. Do NOT use `await db.delete()`.

---

### Decision 6: Docker for Deployment (Standard Setup)

**Date**: March 2, 2026  
**Decided by**: Daya (BE Lead)  
**Status**: ✅ LOCKED

**What**: Docker + docker-compose for local + prod.  
**Why**:
- Reproducible environments
- Easy onboarding for new team members
- Consistent dev/prod
- Standard for accelerator projects

**What was considered**:
- ❌ Plain venv: Works but env drift issues
- ✅ Chosen: Docker + docker-compose

**Trigger**: Do NOT suggest alternatives (k8s, poetry, conda).

---

### Decision 7: Pytest for Testing

**Date**: March 3, 2026  
**Decided by**: Daya (BE Lead)  
**Status**: ✅ LOCKED

**What**: Pytest + pytest-asyncio for async tests.  
**Why**:
- Standard for FastAPI projects
- Great async support
- Simple fixture system

**What was considered**:
- ❌ unittest: More boilerplate
- ✅ Chosen: Pytest

**Trigger**: Do NOT suggest unittest or alternative frameworks.

---

## 🟡 Settling Decisions

### Decision 8: Switch to Mistral (from Llama)

**Date**: March 29, 2026  
**Decided by**: Daya (BE Lead) + AI Lead  
**Status**: 🟡 SETTLING (API contract finalizing)

**What**: Use Mistral AI instead of Groq Llama 3.3 70B.  
**Why**:
- Better reasoning for complex ticket classification
- Competitive pricing
- Mistral platform support

**What's still being finalized**:
- 🔄 Exact model version (`mistral-medium`, `mistral-large`, custom?)
- 🔄 API response format (confirm `priority`, `category`, `action` fields)
- 🔄 Latency benchmarks (is 2-3s target still feasible?)
- 🔄 Cost tracking (is <$500/month pilot budget OK?)

**Trigger**: Check AI-Lead repo for latest before suggesting AI-related changes. Ask AI Lead if API format changed.

---

### Decision 9: JWT Authentication

**Date**: March 20, 2026  
**Decided by**: BE Dev 1 (ongoing implementation)  
**Status**: 🟡 IN PROGRESS

**What**: JWT tokens for API authentication.  
**Why**:
- Stateless (scales well)
- Standard for APIs
- Frontend can store + pass easily

**What's still being finalized**:
- 🔄 Token expiry (1 hour? 24 hours?)
- 🔄 Refresh token flow
- 🔄 Role/permission structure
- 🔄 User model (how do agents sign up?)

**Trigger**: Before adding any permission logic, sync with BE Dev 1. Don't assume roles/permissions exist.

---

### Decision 10: RAG Pipeline for Context

**Date**: March 22, 2026  
**Decided by**: AI Dev + Daya (BE Lead)  
**Status**: 🟡 IN PROGRESS (AI Dev building)

**What**: Use historical tickets as context for AI classification (RAG).  
**Why**:
- Better classification accuracy by showing similar past tickets
- Reduces hallucination risk
- Supports multi-turn reasoning

**What's still being finalized**:
- 🔄 Vector DB choice (Pinecone? Weaviate? Chroma?)
- 🔄 Embedding model (OpenAI? Mistral embeddings?)
- 🔄 How many past tickets to retrieve (top 5? top 10?)
- 🔄 How to integrate with ticket creation flow

**Trigger**: Don't assume RAG is live yet. It's AI Dev's scope. Don't change ticket schema without confirming with AI Dev.

---

## ❌ Rejected Decisions

### Rejected 1: Celery + Redis Queue

**Date**: March 15, 2026  
**Proposed by**: Early brainstorm  
**Status**: ❌ REJECTED

**Reason**: Load doesn't justify complexity. See Decision 1.

**If it comes up again**: "We decided direct HTTP is simpler for pilot load. Revisit post-launch."

---

### Rejected 2: GraphQL API

**Date**: March 10, 2026  
**Proposed by**: Frontend discussion  
**Status**: ❌ REJECTED

**Reason**: One frontend team, tight timeline, REST is sufficient.

**If it comes up again**: "GraphQL is post-MVP. REST + OpenAPI keeps us shipping fast."

---

### Rejected 3: Complex RBAC (Admin/Supervisor/Agent/etc.)

**Date**: March 18, 2026  
**Proposed by**: Product thinking  
**Status**: ❌ REJECTED

**Reason**: Pilot has 5 agents, all same permissions. Complexity not justified.

**If it comes up again**: "RBAC is v2 feature. MVP has one permission level."

---

### Rejected 4: Custom ML Fine-Tuning

**Date**: March 25, 2026  
**Proposed by**: "Can we train on our data?"  
**Status**: ❌ REJECTED

**Reason**: Timeline + data collection overhead. Base model is strong enough.

**If it comes up again**: "Fine-tuning is post-MVP. Focus on feedback loops first."

---

### Rejected 5: Real-Time WebSockets

**Date**: March 19, 2026  
**Proposed by**: "Live agent dashboard"  
**Status**: ❌ REJECTED

**Reason**: Polling is good enough for pilot. WebSockets complexity not needed.

**If it comes up again**: "WebSockets are nice-to-have. Polling works for current dashboard."

---

### Rejected 6: Custom Analytics Dashboard

**Date**: March 24, 2026  
**Proposed by**: "Need to track metrics"  
**Status**: ❌ REJECTED

**Reason**: Use simple DB queries + logs until scale requires it.

**If it comes up again**: "Build dashboards in v2. Now we use Grafana/logs."

---

## 🚧 Open Questions

Questions still being resolved (don't propose solutions until these are answered):

### Q1: Should deleted tickets be soft-deleted or hard-deleted?
**Status**: 🔄 PENDING  
**Stakeholders**: Daya (BE Lead), AI Dev (affects RAG history)  
**Decision timeline**: By April 5, 2026

### Q2: Should we rate-limit the `/tickets/` endpoint?
**Status**: 🔄 PENDING  
**Stakeholders**: Daya (BE Lead), Frontend (might impact UX)  
**Decision timeline**: By April 1, 2026 (before load testing)

### Q3: What's the exact cutoff for "urgent" vs "high" priority?
**Status**: 🔄 PENDING  
**Stakeholders**: AI Lead (Mistral prompt), Support team (workflow expectations)  
**Decision timeline**: By March 31, 2026 (before AI testing)

---

## 📋 Decision Template (for new decisions)

When you need to decide something:

```markdown
### Decision N: [Concise Title]

**Date**: [ISO date]  
**Decided by**: [Names + roles]  
**Status**: 🟢 LOCKED / 🟡 SETTLING / 🔄 PENDING / ❌ REJECTED

**What**: [One sentence description]

**Why**: [2-3 bullet points]
- Reason 1
- Reason 2
- Reason 3

**What was considered**:
- ❌ Option A: Why not
- ✅ Chosen: Why this one

**Tradeoff**: [What we're giving up]

**Trigger**: [When to revisit? Under what conditions?]
```

---

## 🔍 How to Use This Log

1. **Before suggesting architecture changes**: Check if it's already decided + locked.
2. **If locked**: Reference the decision log, don't revisit.
3. **If settling**: Say "I see this is still being finalized. Let me know once you decide."
4. **If rejected**: Don't suggest it again.
5. **If open question**: Highlight it, get answer before proposing solution.

---

**Last Updated**: March 29, 2026 (Mistral switch)  
**Next Review**: April 5, 2026 (Post-integration testing)  
**Maintained by**: Daya (BE Lead)
