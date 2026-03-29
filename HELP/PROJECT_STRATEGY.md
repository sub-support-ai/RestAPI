# Support Tickets AI — Project Strategy & Vision

## 🎯 Project Vision

**Goal**: Build an AI-powered support ticket system that resolves the majority of support requests **autonomously**, with **human-in-the-loop confirmation** rather than full automation.

**Core Value Prop**: 
- Reduce support team workload by 60-70% through AI auto-classification and routing
- Maintain human control: agents approve/modify AI-suggested tickets before creation
- Scale support with minimal hiring

**Not a chatbot**. Not a pure AI replacement. **A force multiplier** for human support teams.

---

## 📊 Current Stage

**Accelerator Program**: First-year student team (8 people), ~4 months into structured development

**Timeline**:
- Week 1-6: Stack setup, DB schema, core API ✅
- Week 7-12: AI integration, frontend, testing (YOU ARE HERE)
- Week 13-16: Integration, presentation, user testing
- Post-launch: Scaling, feedback loops

**Constraint**: Tight timeline + distributed team = high coordination cost. **Every architectural decision must unblock multiple teams simultaneously.**

---

## 🏛️ Architecture Philosophy

### What We Chose & Why

**Direct HTTP calls (not Celery/Redis)**
- ✅ Reason: AI latency is already ~2-3s per request. Queue overhead adds complexity without value.
- ✅ Scales to 1000 tickets/day easily with FastAPI's async.
- ⚠️ Tradeoff: Ticket processing is synchronous. If AI Service dies, users see timeouts (handled by fallback).

**Text priorities (not enum)**
- ✅ Reason: AI Lead can adjust priority labels without BE deployments.
- ✅ Flexible for experimentation (e.g., "urgent-security", "urgent-billing" later).
- ⚠️ Tradeoff: Requires validation on every request.

**One-click ticket confirmation UI**
- ✅ Reason: Agents approve AI classification before DB commit.
- ✅ Reduces false negatives (auto-routing wrong tickets).
- ⚠️ Means frontend must ALWAYS call `/confirm` endpoint (not auto-create).

**Concatenation in Backend (not Frontend)**
- ✅ Reason: AI Service receives single `ticket_text` field = simpler contract.
- ⚠️ Means: BE is responsible for formatting, not AI Lead.

---

## 🚫 Anti-Patterns: What NOT to Suggest

### 1. **Don't recommend adding Celery/Redis**
- **Why it's tempting**: "Decouple ticket processing from request cycle!"
- **Why it's wrong here**: 
  - Adds complexity during tight timeline
  - Introduces new failure modes (queue crashes, workers hanging)
  - You already handle fallbacks in `ai_classifier.py`
  - Load doesn't justify it (~100 tickets/day in pilot)
- **If it comes up**: "Celery is premature optimization. Let's monitor response times in production first."

### 2. **Don't suggest turning priorities into SQL enums**
- **Why it's tempting**: "Type safety! Consistency!"
- **Why it's wrong here**:
  - Breaks AI Lead's ability to experiment with priority labels
  - Requires DB migrations + BE deployments for label changes
  - Text validation is fast enough
  - PostgreSQL supports CHECK constraints for validation if needed
- **If it comes up**: "Enum locked the schema. Text + validation gives AI Lead flexibility."

### 3. **Don't auto-create tickets without frontend confirmation**
- **Why it's tempting**: "Fewer clicks! Faster workflow!"
- **Why it's wrong here**:
  - AI classification is ~85% accurate (hallucination risk)
  - One wrong auto-routed ticket = support team wastes 10 minutes untangling
  - Confirmation UI is THE user feedback loop for improving classification
- **If it comes up**: "Auto-routing without approval kills trust in the system. One-click confirm is the business model."

### 4. **Don't build custom ML training pipeline**
- **Why it's tempting**: "Fine-tune Mistral on your own tickets!"
- **Why it's wrong here**:
  - You have <6 weeks to demo. Fine-tuning = 2 weeks setup + data collection
  - Mistral base model is already strong (matches GPT-3.5 on benchmarks)
  - Better use time building confidence through human feedback loops
- **If it comes up**: "Fine-tuning is post-launch. Now we validate base model + gather feedback."

### 5. **Don't add GraphQL/multiple API versions yet**
- **Why it's tempting**: "Future-proof! Mobile optimization!"
- **Why it's wrong here**:
  - You have ONE frontend team right now
  - REST + OpenAPI auto-docs is enough
  - Adding GraphQL = 3 days of rewiring + testing
  - Premature optimization during crunch time
- **If it comes up**: "REST keeps us fast. GraphQL after we validate market fit."

### 6. **Don't over-engineer user roles/permissions**
- **Why it's tempting**: "RBAC! Admin, supervisor, agent roles!"
- **Why it's wrong here**:
  - Pilot has ~5 support agents, all need same permissions
  - Complex permissions = complex testing = fewer tickets to test on
  - Better to nail core flow first, add RBAC in v2
- **If it comes up**: "RBAC is nice-to-have. Let's ship with one role level first."

### 7. **Don't store sensitive data (customer names, emails, PII) as plain text**
- **Why it matters**: GDPR/privacy.
- **If it comes up**: "At least hash customer emails, separate PII schema."

### 8. **Don't build custom vector DB/RAG from scratch**
- **Why it's tempting**: "Our data, our vectors!"
- **Why it's wrong here**:
  - RAG is AI Dev's job, not yours
  - Pinecone/Weaviate connectors already exist
  - Let AI Dev own this, integrate via API
- **If it comes up**: "RAG is in-scope for AI Dev. BE just calls the endpoint."

### 9. **Don't assume tickets are always created via chat**
- **Why it matters**: Roadmap has email/Slack integrations later
- **If it comes up**: "Keep ticket creation endpoint generic (title + body). Don't hard-code chat-only assumptions."

### 10. **Don't skip error messages that help debugging**
- **Why it's tempting**: "Ship faster without logs!"
- **Why it's wrong here**:
  - AI integration is new territory. You'll debug Mistral timeouts, parsing errors, etc.
  - Good error logs = 30 min debug vs 3 hour hunt
- **If it comes up**: "Log every AI call + response. Include timestamps, request/response size."

---

## 🎯 Success Metrics (for context)

These define what "done" looks like:

| Metric | Target | Why |
|--------|--------|-----|
| AI accuracy | 85%+ | Threshold for human approval trust |
| Ticket creation latency | <5s | Acceptable for synchronous UI |
| System uptime | 99% | Pilot SLA |
| Support agent adoption | 80%+ | If agents hate it, project fails |
| Mistral API cost | <$500/month (pilot) | Budget constraint |

**Anything that jeopardizes these = risky suggestion.**

---

## 🔗 Integration Points (What Can Break Alignment)

### Frontend Team Dependency
- **Chat Interface** → sends `title` + `body` → Expects `/tickets/` to respond in <5s
- **Risk**: If you add complex preprocessing, response time degrades
- **Mitigation**: Any pre-processing should be <100ms

### AI Lead Dependency
- **Sends**: `ticket_text` field (BE concatenates)
- **Expects**: `category`, `priority`, `action` back
- **Risk**: If response format changes, AI Lead's parser breaks
- **Mitigation**: **Lock the API contract**. Any schema change = notify AI Lead 48 hours ahead

### AI Dev Dependency
- **RAG Pipeline** → queries ticket history → Mistral LLM
- **Expects**: Tickets to have consistent `status`, `category`, `priority` fields
- **Risk**: If you change status enum without warning, RAG breaks
- **Mitigation**: **Migrate data** when changing schema. Test with AI Dev.

---

## ⚡ Decision Framework

**When I suggest something, ask: Does it...**

1. **Unblock multiple teams** simultaneously? (Good)
2. **Add complexity without value** before MVP? (Bad)
3. **Maintain human approval loop** in the workflow? (Good)
4. **Lock down flexibility** that AI Lead needs? (Bad)
5. **Help debug Mistral issues** (logging, error handling)? (Good)
6. **Require 3+ days implementation** during crunch? (Bad unless critical)

---

## 📋 Current Blockers (Keep in Mind)

- **Mistral Integration**: Just switched from Llama. API contract still settling.
- **Frontend Authentication**: BE Dev 1 working on JWT. Don't assume auth is done.
- **RAG Pipeline**: AI Dev still building. Don't commit to specific DB schema for RAG yet.
- **Accelerator Timeline**: Demo in ~6 weeks. Every task must ship incrementally.

---

## 🚀 What Success Looks Like at Demo

**Not**: "We built every feature perfectly"

**Yes**: 
- ✅ AI classifies 100 test tickets with 85%+ accuracy
- ✅ One agent can approve/create tickets in <2 min each
- ✅ System handles 1000 tickets/day without errors
- ✅ Team can explain architecture in 10 minutes
- ✅ Mistral integration is stable (no hallucinations, consistent formatting)

**What kills a demo**:
- ❌ Unexpected downtime (missing error handling)
- ❌ AI returns malformed responses (no validation)
- ❌ Slow ticket creation (>5s latency)
- ❌ Agents confused by UI (frontend struggles)
- ❌ Tight coupling between teams (one team change breaks three others)

---

## 🎓 Mentorship Context (Your Other Role)

You're also mentoring a student team on **Rosneft AI assistant**.

**Key principle**: Apply these same architectural lessons to your mentees.
- Start simple, don't over-engineer
- Lock API contracts early
- Keep teams unblocked from each other
- Validate with users early (not perfect products)

---

## Last Updated
**March 29, 2026** — After Mistral switchover from Llama  
**Status**: In integration phase, timeline tight, demo in ~6 weeks
