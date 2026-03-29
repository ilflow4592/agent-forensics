# Agent Forensics

**Black box for AI agents.** Capture every decision, auto-detect failure patterns, generate forensic reports for EU AI Act compliance.

When an AI agent makes a wrong purchase, leaks data, or fails silently — you need to know **why**. Agent Forensics records every decision point, tool call, and LLM interaction, then reconstructs the causal chain and auto-classifies what went wrong.

## Why

- **EU AI Act** (Aug 2026): High-risk AI systems must provide decision traceability. Fines up to €35M or 7% of global revenue.
- **AI agents are already causing incidents**: unauthorized purchases, fabricated customer responses, silent data leaks.
- **No existing tool** reconstructs the *why* behind agent failures. Monitoring tools watch in real-time. Forensics analyzes after the fact.

## Key Features

- **Framework-agnostic** — works with any agent (LangChain, OpenAI, CrewAI, or custom)
- **One-line integration** — add a callback handler, get full forensics
- **6 failure patterns** — auto-detected with severity and evidence
- **Prompt drift detection** — catches when system prompts change mid-session
- **Deterministic replay** — reproduce and compare agent runs
- **Compliance-ready** — reports aligned with EU AI Act Article 14

## Quick Example

```python
from agent_forensics import Forensics

f = Forensics(session="order-123", agent="shopping-agent")

f.decision("search_products", input={"query": "mouse"}, reasoning="User request")
f.tool_call("search_api", input={"q": "mouse"}, output={"results": [...]})
f.guardrail(intent="check price", action="purchase", allowed=True, reason="Within budget")
f.finish("Ordered Logitech M750 for $45")

# Generate forensic report
print(f.report())

# Auto-classify failures
failures = f.classify()
```

## Architecture

```
Your Agent (any framework)
    │
    │  Callback / Hook (1 line of code)
    ▼
┌───────────────────────────┐
│  Forensics Collector       │  Captures decisions, tool calls, LLM interactions
├───────────────────────────┤
│  Context & Prompt Tracker  │  Tracks RAG injections + prompt drift
├───────────────────────────┤
│  Event Store (SQLite)      │  Immutable event log with session isolation
├───────────────────────────┤
│  Failure Classifier        │  Auto-detects 6 failure patterns
├───────────────────────────┤
│  Report Generator          │  Markdown / PDF / Dashboard
├───────────────────────────┤
│  Replay Engine             │  Deterministic trace reproduction + diff
└───────────────────────────┘
```

## Next Steps

- [Getting Started](getting-started.md) — install and generate your first report
- [API Reference](api-reference.md) — full method documentation
- [Integrations](integrations.md) — LangChain, OpenAI Agents SDK, CrewAI
- [Failure Patterns](failure-patterns.md) — what each pattern means and how to fix it
- [EU AI Act Compliance](eu-ai-act.md) — how Agent Forensics maps to Article 14
