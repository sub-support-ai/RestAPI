# 🚀 START HERE: How to Use Your Claude Context System

**You just created a system where Claude (any AI assistant) understands your project at a strategic level, not just code level.**

---

## What You Created

6 documents (total ~50 KB) that form a "knowledge base" for Claude:

1. **QUICK_START.txt** ← Read this first (2 min cheat sheet)
2. **CLAUDE_CONTEXT.md** ← Tech details (what's the stack?)
3. **PROJECT_STRATEGY.md** ← Why you chose things (what NOT to suggest?)
4. **TEAM_CONTRACTS.md** ← Inter-team agreements (who breaks if I change X?)
5. **DECISION_LOG.md** ← History of decisions (was this already decided?)
6. **README.md** ← How to use all 5 docs

---

## Right Now: Copy Files to Your Repo

```powershell
# Windows (from Claude's /home/claude to your project)
Copy-Item "C:\path\to\CLAUDE_CONTEXT.md" "C:\path\to\MainFastAPI\"
Copy-Item "C:\path\to\PROJECT_STRATEGY.md" "C:\path\to\MainFastAPI\"
Copy-Item "C:\path\to\TEAM_CONTRACTS.md" "C:\path\to\MainFastAPI\"
Copy-Item "C:\path\to\DECISION_LOG.md" "C:\path\to\MainFastAPI\"
Copy-Item "C:\path\to\README.md" "C:\path\to\MainFastAPI\"
Copy-Item "C:\path\to\QUICK_START.txt" "C:\path\to\MainFastAPI\"

# Then commit
cd C:\path\to\MainFastAPI
git add *.md *.txt
git commit -m "docs: add Claude context system"
```

---

## Next: Use in Claude Code / CLI

```bash
# 1. Open your project
cd path/to/MainFastAPI

# 2. Start Claude Code, first message:
"Read CLAUDE_CONTEXT.md, PROJECT_STRATEGY.md, and DECISION_LOG.md.
I'm the Backend Lead on Support Tickets AI. Help me with [TASK]."

# 3. Claude loads context, gives aligned advice
```

---

## Quick File Purposes

| File | When to Read | Why |
|------|--------------|-----|
| QUICK_START.txt | "2-min overview" | Cheat sheet |
| CLAUDE_CONTEXT.md | "What's the tech stack?" | Endpoints, schema |
| PROJECT_STRATEGY.md | "Why this architecture?" | Anti-patterns |
| TEAM_CONTRACTS.md | "If I change X, who breaks?" | Dependencies |
| DECISION_LOG.md | "Was this decided?" | History |
| README.md | "How do I use this?" | Guide |

---

## 3 Most Important Things

1. **Locked decisions don't change** (Direct HTTP, text priorities, one-click confirm)
2. **Team dependencies are real** (Notify teams on schema changes)
3. **Timeline is tight** (6 weeks to demo, every decision matters)

---

**Copy files → Commit → Try in Claude Code → Done.** 🚀

