# Claude Context System for Support Tickets AI

This directory contains **4 strategic documents** that give Claude (and any AI assistant) deep understanding of your project beyond just the code.

---

## 📚 Documents Overview

### 1. **CLAUDE_CONTEXT.md** — Technical Project Info
**What**: Code architecture, stack, API endpoints, team roles, current status.

**When to read it**: "What's the tech stack? How do we call the AI Service?"

**Key sections**:
- Tech stack (FastAPI, PostgreSQL, Mistral, etc.)
- Database schema
- Current endpoints
- Team structure
- SQLAlchemy patterns + anti-patterns
- Test commands
- Environment variables

**Use case**: New team member, onboarding to codebase, understanding API contracts.

---

### 2. **PROJECT_STRATEGY.md** — Vision, Goals, Anti-Patterns
**What**: Why you built this way, what NOT to suggest, success metrics.

**When to read it**: "Should we add feature X?" "Is this approach wise?"

**Key sections**:
- Project vision (force multiplier for support teams, not full automation)
- Current stage (accelerator MVP, 6-week timeline)
- Architecture philosophy (why direct HTTP, why text priorities, etc.)
- 10 anti-patterns with reasoning (Celery, GraphQL, RBAC, fine-tuning, etc.)
- Success metrics (85% accuracy, <5s latency, 99% uptime)
- Integration dependencies (what breaks if you change something)
- Decision framework (does this decision unblock or block teams?)

**Use case**: Decision-making, preventing bad suggestions, understanding constraints.

---

### 3. **TEAM_CONTRACTS.md** — Inter-Team API Agreements
**What**: Explicit contracts between teams (BE ↔ Frontend, BE ↔ AI Lead, etc.)

**When to read it**: "If I change X, who breaks?" "What does Frontend expect?"

**Key sections**:
- 5 core contracts (BE ↔ AI Lead, BE ↔ Frontend, BE ↔ AI Dev, etc.)
- Locked response schemas (don't change without sync)
- Breaking changes checklist
- Notification protocol (how to tell teams about changes)
- Health check questions

**Use case**: Preventing breaking changes, understanding downstream impact, knowing who to notify.

---

### 4. **DECISION_LOG.md** — Historical Decisions + Reasoning
**What**: Why you chose X over Y, what was rejected, what's still open.

**When to read it**: "Why don't we use Celery?" "Is JWT done yet?"

**Key sections**:
- ✅ Locked decisions (Direct HTTP, text priorities, one-click confirm, etc.)
- 🟡 Settling decisions (Mistral switchover, JWT auth, RAG pipeline)
- ❌ Rejected decisions (Celery, GraphQL, RBAC, fine-tuning, WebSockets, custom dashboards)
- 🔄 Open questions (soft vs hard delete, rate limiting, priority cutoffs)

**Use case**: Not re-suggesting already-decided things, understanding rationale, knowing what's in-progress.

---

## 🎯 How to Use These Docs

### Workflow 1: Claude Code / CLI Workflow

```bash
# 1. Open your project in Claude Code / CLI
cd path/to/MainFastAPI

# 2. In first message to Claude, ask it to read context
"Read CLAUDE_CONTEXT.md and PROJECT_STRATEGY.md. I need help with [task]."

# 3. Claude reads files, understands your project, gives advice aligned with:
#    - Your architecture choices
#    - Your timeline constraints
#    - Your team dependencies
#    - What's already been decided
```

### Workflow 2: Quick Question

```
"Should I add Celery for async task processing?"
→ Claude: "I see in PROJECT_STRATEGY.md that you rejected this 
   because load doesn't justify complexity. Let's focus on direct HTTP."
```

### Workflow 3: Integration Question

```
"I need to change the ticket response schema."
→ Claude: "TEAM_CONTRACTS.md shows this is locked until post-MVP. 
   Who needs to approve this change? Frontend, AI Dev, AI Lead. 
   Here's the notification template..."
```

### Workflow 4: Decision Rationale

```
"Why text priorities instead of SQL enum?"
→ Claude: "DECISION_LOG.md explains: AI Lead can experiment with labels 
   without DB migrations. Type safety trade-off is acceptable."
```

---

## 🔄 Keeping Docs Updated

**When you make an architectural decision**:

1. Add entry to `DECISION_LOG.md` (copy template)
2. Update relevant section in `PROJECT_STRATEGY.md` or `TEAM_CONTRACTS.md`
3. Commit with message like: `docs: log decision to use Mistral over Llama`

**When you finish a feature**:

1. Update `CLAUDE_CONTEXT.md` status checkbox
2. Update team in `TEAM_CONTRACTS.md` if API changed

**When timeline/goals shift**:

1. Update `PROJECT_STRATEGY.md` timeline section
2. Update success metrics if they changed

**When you onboard new team member**:

1. Have them read in order: `CLAUDE_CONTEXT.md` → `PROJECT_STRATEGY.md` → `TEAM_CONTRACTS.md`
2. Point them to relevant `DECISION_LOG.md` entries for context

---

## 📋 Quick Reference

| Question | Read This |
|----------|-----------|
| "What's the tech stack?" | CLAUDE_CONTEXT.md |
| "Why this architecture?" | PROJECT_STRATEGY.md |
| "Why not Celery/GraphQL/RBAC?" | PROJECT_STRATEGY.md (anti-patterns) |
| "What does Frontend expect from `/tickets/`?" | TEAM_CONTRACTS.md |
| "If I change priorities schema, who breaks?" | TEAM_CONTRACTS.md |
| "Was this already decided?" | DECISION_LOG.md |
| "Is JWT auth done yet?" | DECISION_LOG.md |
| "What's the success metric for accuracy?" | PROJECT_STRATEGY.md |

---

## 🚀 Pro Tips

### Tip 1: Use with Claude AI Web
Paste all 4 docs at start of conversation, then ask questions. Claude will reference them.

### Tip 2: Use with Claude Code / CLI
Ask Claude to read them at the start: `"Read CLAUDE_CONTEXT.md, PROJECT_STRATEGY.md, and DECISION_LOG.md. Then help me with..."`

### Tip 3: Share with New Team Members
Send these 4 files instead of verbal explanations. They'll onboard 10x faster.

### Tip 4: Use Before Meetings
Before team sync, update DECISION_LOG.md with decisions from last sync. Reference in next meeting.

### Tip 5: Version in Git
Commit updates to these files just like code. They're living documentation.

```bash
git add CLAUDE_CONTEXT.md DECISION_LOG.md PROJECT_STRATEGY.md TEAM_CONTRACTS.md
git commit -m "docs: update Mistral integration status in context + decision log"
```

---

## 📞 Example: Using Full System

**Scenario**: You ask Claude for advice on a new feature.

```
Me: "Should we add an email-to-ticket integration endpoint?"

Claude: [Reads all 4 docs]

"Looking at PROJECT_STRATEGY.md, I see email integration is in the 
roadmap but post-launch. CLAUDE_CONTEXT.md shows you're in MVP phase 
with 6 weeks to demo. 

TEAM_CONTRACTS.md shows the ticket creation endpoint design assumes 
title+body input. Email integration would require significant refactoring 
to the contract between Frontend and BE.

Recommendation: Defer email integration to v2. Focus on shipping chat 
integration + proving accuracy first.

But IF you do it, you'd need to:
1. Notify all teams (TEAM_CONTRACTS.md notification protocol)
2. Add decision entry to DECISION_LOG.md
3. Possibly modify ticket schema (data migration plan required)"
```

Instead of generic advice, Claude gives **context-aware, aligned** recommendations.

---

## ⚠️ When Docs Get Out of Sync

If Claude suggests something that contradicts reality:

1. Check if docs are outdated
2. Update docs first
3. Then re-ask Claude

Example:
```
Claude: "I see you rejected WebSockets. Good call. Polling is fine."
You: "Wait, we actually need WebSockets now for live dashboard."
→ Update DECISION_LOG.md: Move WebSockets from ❌ REJECTED to 🟡 SETTLING
→ Re-ask: Claude will now recommend WebSocket patterns.
```

---

## 🎓 For Your Mentorship Role

Use **the same system** with your Rosneft student team:

1. Have them create `PROJECT_STRATEGY.md` (vision, not code)
2. Document their `TEAM_CONTRACTS.md` (who owns what API)
3. Build `DECISION_LOG.md` (why they chose tech stack)

This teaches:
- Architecture thinking (not just coding)
- Team coordination (not just individual tasks)
- Decision rationale (not just "because tutorial said so")

---

## 📊 Document Maintenance Checklist

- [ ] Weekly: Update DECISION_LOG.md with new decisions
- [ ] Bi-weekly: Review PROJECT_STRATEGY.md constraints (timeline, budget)
- [ ] Per sprint: Update CLAUDE_CONTEXT.md status section
- [ ] Before meetings: Ensure TEAM_CONTRACTS.md reflects current APIs
- [ ] End of month: Review all docs for consistency

---

**Last Updated**: March 29, 2026  
**Maintained by**: Daya (BE Lead)  
**Next review**: April 5, 2026 (post-Mistral integration)

---

## Questions?

If Claude suggests something that doesn't match these docs:
1. Check if docs are current
2. Update docs
3. Re-ask Claude

If you disagree with something in the docs:
1. Update it (they're yours)
2. Commit the change
3. Share with team

These docs are **living, evolving guides**, not fixed policies.
