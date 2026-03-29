# Support Tickets AI — Team API Contracts

**Purpose**: Explicit agreements between teams to prevent scope creep and keep integration smooth.

---

## 🤝 Contract 1: BE ↔ AI Lead (Mistral Integration)

### BE Responsibility
- ✅ Receive `title` + `body` from frontend
- ✅ **Concatenate** into single `ticket_text` field: `f"{title}\n\n{body}"`
- ✅ Call AI Service with: `POST /classify` with body `{"ticket_text": "..."}`
- ✅ **Parse response** as JSON: `{"priority": "...", "category": "...", "action": "..."}`
- ✅ Validate response format (catch malformed JSON, missing fields)
- ✅ Return fallback classification if Mistral times out (>5s): `("medium", "general", "create")`
- ✅ Log all requests/responses with timestamps for debugging
- ✅ Handle Mistral API errors gracefully (no stack traces to frontend)

### AI Lead Responsibility
- ✅ Provide stable Mistral API endpoint
- ✅ Document exact request/response schema
- ✅ Return consistent priority values: `["low", "medium", "high", "urgent"]` or variants
- ✅ Return consistent category values: agree on list (e.g., `["billing", "technical", "account"]`)
- ✅ Return action field: `"create"` (accept) or `"decline"` (reject)
- ✅ Keep response latency <3s (p95)
- ✅ **Notify BE 48 hours before** any schema changes

### What NOT to Do
- ❌ AI Lead: Don't expect BE to pre-process text (lemmatization, entity extraction)
- ❌ BE: Don't build custom prompt engineering. Use the endpoint as-is.
- ❌ Either: Don't change the schema without sync. This is THE contract.

---

## 🤝 Contract 2: BE ↔ Frontend (Chat Interface)

### Frontend Responsibility
- ✅ Collect user message as `message` (required)
- ✅ Allow optional `title` override (advanced users)
- ✅ If `title` not provided, use first 50 chars of message as title
- ✅ Send to BE: `POST /tickets/` with `{"title": "...", "body": "...", "user_id": "..."}`
- ✅ Display AI classification to user before confirmation
- ✅ Call `POST /tickets/{id}/confirm` only after user approval
- ✅ Show ticket ID + confirmation to user after creation
- ✅ Handle BE errors: show friendly error messages (not JSON stack traces)

### BE Responsibility
- ✅ Accept `POST /tickets/` (title + body)
- ✅ Return ticket object with AI classification + `status: "pending_confirmation"`
- ✅ Provide `POST /tickets/{id}/confirm` endpoint to mark as `created`
- ✅ **Never auto-create** tickets. Always require confirm.
- ✅ Response time: <5s (includes AI call)
- ✅ Return clear error messages on validation failures

### What NOT to Do
- ❌ Frontend: Don't auto-submit tickets. Always wait for user confirm.
- ❌ BE: Don't create tickets without explicit confirm call.
- ❌ Frontend: Don't ask for category/priority — AI provides those.
- ❌ Either: Don't change response schema without sync.

---

## 🤝 Contract 3: BE ↔ AI Dev (RAG Pipeline)

### BE Responsibility
- ✅ Store tickets with consistent schema:
  - `id`: UUID
  - `title`: string
  - `body`: string
  - `user_id`: string
  - `status`: one of `["pending_confirmation", "created", "declined", "resolved"]`
  - `category`: string (from AI classification)
  - `priority`: string (from AI classification)
  - `created_at`, `updated_at`: timestamps
- ✅ Provide `GET /tickets/` endpoint with filters (optional: `status`, `category`, `priority`)
- ✅ **Don't change status enum** without notifying AI Dev
- ✅ Keep ticket history immutable (no edits to past tickets)

### AI Dev Responsibility
- ✅ Query `GET /tickets/` to fetch historical context for RAG
- ✅ Use `category`, `priority`, `status` for ranking/filtering
- ✅ Notify BE before schema assumptions change
- ✅ **Don't assume** ticket order or sorting order

### What NOT to Do
- ❌ BE: Don't change `status` enum mid-integration. Data migration hell.
- ❌ AI Dev: Don't assume tickets are sorted by date (query explicitly).
- ❌ BE: Don't store custom fields without documenting (RAG needs schema stability).
- ❌ Either: Don't skip migrations when schema changes.

---

## 🤝 Contract 4: BE ↔ BE Dev 2 (Routing Logic)

### BE Dev 1 (You) Responsibility
- ✅ Own core ticket CRUD + AI classification flow
- ✅ Provide `/tickets/` endpoints (create, read, list, update, delete)
- ✅ Manage `pending_confirmation` → `created` state transition
- ✅ Delegate routing logic to BE Dev 2 **after ticket is confirmed**

### BE Dev 2 Responsibility
- ✅ Own post-creation routing (assign to queue, notify agent, escalate)
- ✅ Handle `status: "created"` tickets via webhook or polling
- ✅ Don't modify ticket data (only route/assign)
- ✅ Notify BE if routing fails (for error handling)

### What NOT to Do
- ❌ You: Don't build routing logic. Keep it simple.
- ❌ BE Dev 2: Don't modify ticket content. Only route.
- ❌ Either: Don't create circular dependencies (routing affects classification, etc.)

---

## 🤝 Contract 5: BE ↔ JWT/Auth Team (BE Dev 1)

### Auth Team Responsibility
- ✅ Provide JWT token generation endpoint
- ✅ Provide token validation middleware
- ✅ Document token format + expiry
- ✅ Provide user/role extraction from token

### BE Responsibility
- ✅ Protect all endpoints with JWT validation
- ✅ Reject requests without valid token (401)
- ✅ Extract `user_id` from token for ticket ownership
- ✅ Don't implement custom auth (use middleware)

### What NOT to Do
- ❌ Either: Don't skip token validation on any endpoint
- ❌ You: Don't build custom auth. Use the middleware.
- ❌ Auth: Don't change token format without BE sync.

---

## 📋 Response Schema Lock

These schemas are **LOCKED** until post-MVP:

### `POST /tickets/` → Response
```json
{
  "id": "uuid",
  "title": "string",
  "body": "string",
  "user_id": "string",
  "status": "pending_confirmation",
  "priority": "string",
  "category": "string",
  "action": "string",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```
**Changes require**: All team leads agreement + data migration plan.

### `POST /tickets/{id}/confirm` → Response
```json
{
  "id": "uuid",
  "status": "created",
  "confirmed_at": "ISO8601"
}
```
**Lock**: Status changed from `pending_confirmation` → `created`.

### AI Service Response (`/classify` endpoint)
```json
{
  "priority": "string",
  "category": "string",
  "action": "string"
}
```
**Lock**: AI Lead controls this schema. BE only consumes.

---

## ⚠️ Breaking Changes Checklist

If you need to change schema, ask:

- [ ] **Is this essential for MVP?** (If no, defer to v2)
- [ ] **Did I notify all dependent teams?** (AI Dev, Frontend, AI Lead)
- [ ] **Do I have data migration plan?** (Can't break existing tickets)
- [ ] **Did I update tests?** (Contract compliance tests)
- [ ] **Is timeline still on track?** (Do I have implementation time?)

If all checks pass: Schedule 30-min sync with team leads, then implement.

---

## 🔔 Notification Protocol

### When You Make a Change

1. **Small schema change** (new optional field): Slack message to team leads, no sync needed
2. **Breaking change** (field type changes, enum values): 48-hour notice, async feedback, then sync meeting
3. **Endpoint addition**: Slack message with endpoint spec, wait 24h for objections
4. **Critical bug fix**: Post message + implement, inform after (if it's a hot fix)

### Notification Template
```
🔔 [BE Schema Change Incoming]

Endpoint: POST /tickets/
Change: Adding optional field "internal_notes" (string, nullable)
Reason: Support agents need to add notes without creating new ticket
Impact: All teams
Timeline: Implement Friday 9am UTC, deploy Monday
Questions? Reply in thread.
```

---

## 📊 Current Status (as of March 29, 2026)

| Contract | Status | Notes |
|----------|--------|-------|
| BE ↔ AI Lead | 🟡 SETTLING | Just switched to Mistral. Finalizing schema. |
| BE ↔ Frontend | 🟢 LOCKED | Chat interface confirmed. One-click confirm flow. |
| BE ↔ AI Dev | 🟢 LOCKED | RAG pipeline starting. Schema stable. |
| BE ↔ BE Dev 2 | 🟡 SETTLING | Routing logic not started yet. |
| BE ↔ Auth | 🟡 IN PROGRESS | JWT middleware being built. |

---

## ✅ Health Check Questions

If I'm recommending something, ask yourself:

1. **Does it respect these contracts?** (If not, suggest different approach)
2. **Does it require schema changes?** (If yes, do I have approval + migration plan?)
3. **Does it block another team?** (If yes, pause and sync)
4. **Can it wait until post-MVP?** (If yes, defer it)
5. **Is timeline still on track?** (If no, raise flag now)

---

**Last Updated**: March 29, 2026  
**Next Sync**: Mistral integration finalization (AI Lead + BE)  
**By**: Daya (BE Lead) + Team Leads
