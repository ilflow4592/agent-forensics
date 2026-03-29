# Agent Forensics

**Black box for AI agents.** Capture every decision, auto-detect failure patterns, generate forensic reports for EU AI Act compliance.

When an AI agent makes a wrong purchase, leaks data, or fails silently — you need to know **why**. Agent Forensics records every decision point, tool call, and LLM interaction, then reconstructs the causal chain and auto-classifies what went wrong.

![Agent Forensics Dashboard — Incident Session](content/screenshots/02-incident-overview.png)

## Why

- **EU AI Act** (Aug 2026): High-risk AI systems must provide decision traceability. Fines up to €35M or 7% of global revenue.
- **AI agents are already causing incidents**: Meta Sev-1 data leak (Mar 2026), unauthorized purchases, fabricated customer responses.
- **No existing tool** reconstructs the *why* behind agent failures. Monitoring tools watch in real-time. Forensics analyzes after the fact.

## Install

### From PyPI

```bash
pip install agent-forensics              # Core only (manual recording)
pip install agent-forensics[langchain]   # + LangChain integration
pip install agent-forensics[openai-agents]  # + OpenAI Agents SDK
pip install agent-forensics[crewai]      # + CrewAI
pip install agent-forensics[all]         # Everything
```

### From Source

```bash
git clone https://github.com/ilflow4592/agent-forensics.git
cd agent-forensics
pip install -e ".[all]"
```

## Quick Start — Full Walkthrough

### Step 1: Install

```bash
pip install agent-forensics[all]
```

### Step 2: Record agent actions

Choose one of the methods below depending on your setup.

**Option A: Manual recording (any framework or custom agent)**

```python
# save this as demo.py
from agent_forensics import Forensics

f = Forensics(session="order-123", agent="shopping-agent")

# Record decisions and tool calls
f.decision("search_products", input={"query": "mouse"}, reasoning="User requested product search")
f.tool_call("search_api", input={"q": "mouse"}, output={"results": [{"name": "Logitech M750", "price": 45}]})

# Record external context injections (RAG, memory, etc.)
f.context_injection("vector_db", content={
    "document": "refund_policy.md",
    "chunk": "Refunds available within 30 days",
    "similarity_score": 0.92,
})

# Track system prompt changes (auto-detects drift)
f.prompt_state("You are a shopping assistant. Buy the cheapest option.")

# Guardrail checkpoints — was this action allowed?
f.guardrail(intent="check price", action="purchase item", allowed=True, reason="Within budget")

# Record errors and final output
f.error("purchase_failed", output={"reason": "Out of stock"})
f.finish("Could not complete purchase due to stock unavailability.")
```

**Option B: LangChain — auto-capture with one line**

```python
from agent_forensics import Forensics

f = Forensics(session="order-123")
agent.invoke({"input": "..."}, config={"callbacks": [f.langchain()]})
```

Prompt drift detection is automatic — no manual calls needed.

**Option C: OpenAI Agents SDK — auto-capture with one line**

```python
from agent_forensics import Forensics
from agents import Agent, Runner

f = Forensics(session="order-123")
agent = Agent(name="shopper", tools=[...], hooks=f.openai_agents())
result = await Runner.run(agent, "Buy a wireless mouse")
```

Model config (name, temperature, seed) is automatically captured for deterministic replay.

**Option D: CrewAI — auto-capture with callbacks**

```python
from agent_forensics import Forensics

f = Forensics(session="order-123")
hooks = f.crewai()
agent = Agent(role="shopper", step_callback=hooks.step_callback)
task = Task(description="...", agent=agent, callback=hooks.task_callback)
```

### Step 3: Generate reports

```python
# Full Markdown report — timeline + decisions + causal chain + failure classification
print(f.report())

# Save as files
f.save_markdown()   # → forensics-report-order-123.md
f.save_pdf()        # → forensics-report-order-123.pdf
```

### Step 4: Auto-classify failure patterns

```python
# Detect failure patterns in current session
failures = f.classify()
for fail in failures:
    print(f"[{fail['severity']}] {fail['type']} — {fail['description']}")

# Aggregate patterns across all sessions
stats = f.failure_stats()
print(f"Total failures: {stats['total_failures']}")
for ftype, info in stats['by_type'].items():
    print(f"  {ftype}: {info['count']}x")
```

### Step 5: Deterministic replay

```python
# Extract model config + step sequence from a recorded session
config = f.get_replay_config("order-123")
print(config["model_config"])  # {'model': 'gpt-4o', 'temperature': 0, 'seed': 42}

# After re-running your agent with the same config into a new session:
diff = f.replay_diff("order-123", "order-123-replay")
print(f"Matching: {diff['matching']}")
for d in diff['divergences']:
    print(f"  Step {d['step']}: {d['type']}")
```

### Step 6: Launch the web dashboard

```python
f.dashboard(port=8080)  # → http://localhost:8080
```

Or from the command line:

```bash
python -c "from agent_forensics import Forensics; Forensics(db_path='forensics.db').dashboard()"
```

### Step 7: Access raw event data (optional)

```python
events = f.events()
for e in events:
    print(f"[{e.event_type}] {e.action} — {e.reasoning}")

print(f.sessions())  # ['order-123', 'order-456', ...]
```

All events are stored in a local SQLite file (`forensics.db` by default).

---

## Features

### Forensic Report

Every report includes:

- **Timeline** — Chronological record of all agent actions
- **Decision Chain** — Each decision with its reasoning
- **Incident Analysis** — Automatic error detection + root cause chain
- **Causal Chain** — `Decision → Tool Call → Result → Error` trace
- **Failure Classification** — Auto-detected failure patterns with severity and evidence
- **Prompt Drift Analysis** — Detects when system prompt changes between steps
- **Context Injections** — Which RAG documents / memory influenced each decision
- **Compliance Notes** — EU AI Act Article 14 (Human Oversight) support

### Failure Auto-Classification

Agent Forensics automatically detects these failure patterns:

| Pattern | Severity | What It Detects |
|---------|----------|----------------|
| `HALLUCINATED_TOOL_OUTPUT` | HIGH | Agent ignored a tool error and proceeded as if it succeeded |
| `MISSING_APPROVAL` | HIGH | Critical action (purchase, delete, send) without guardrail check |
| `SILENT_SUBSTITUTION` | HIGH | Final output differs from user's original request without approval |
| `PROMPT_DRIFT_CAUSED` | MEDIUM | Decision influenced by a system prompt change between steps |
| `REPEATED_FAILURE` | MEDIUM | Same failing action retried without changing approach |
| `RETRIEVAL_MISMATCH` | MEDIUM | Low-similarity RAG context used (potentially irrelevant) |

### Guardrail Checkpoints

Record whether critical actions were allowed or blocked:

```python
f.guardrail(
    intent="buy Apple Magic Mouse per user request",
    action="purchase Logitech M750",
    allowed=False,
    reason="User explicitly requested Apple Magic Mouse — substitution not allowed"
)
```

Blocked actions trigger incident detection and appear in the causal chain as `[GUARDRAIL BLOCKED]`.

### Context Injection Tracking

Trace which external data influenced each decision:

```python
f.context_injection("vector_db", content={
    "document": "refund_policy_v2.md",
    "similarity_score": 0.92,
}, reasoning="Retrieved refund policy from vector store")
```

Shows up in the causal chain as `[CONTEXT]` nodes — "this decision was influenced by this specific document."

### Prompt Drift Detection

Automatically detects when the system prompt changes between agent steps:

```python
f.prompt_state("You are a helpful assistant.")
# ... agent does work ...
f.prompt_state("You are a helpful assistant. Always choose the cheapest option.")
# → PROMPT DRIFT automatically detected and flagged
```

For LangChain and OpenAI Agents SDK, drift detection is **automatic** — no manual calls needed.

### Deterministic Replay

Extract model config from a recorded session and compare results:

```python
config = f.get_replay_config("order-123")
# → {'model': 'gpt-4o', 'temperature': 0, 'seed': 42}

diff = f.replay_diff("order-123", "order-123-replay")
# → Shows exactly which step diverged and how
```

### Web Dashboard

Dark-themed dashboard with session selector, color-coded timeline, and causal chain visualization.

![Causal Chain — Root Cause Analysis](content/screenshots/04-causal-chain.png)

![Data Leak Incident](content/screenshots/05-data-leak.png)

### Output Formats

- **Markdown** — `f.save_markdown()`
- **PDF** — `f.save_pdf()` (requires `pip install agent-forensics[pdf]`)
- **Web Dashboard** — `f.dashboard(port=8080)`
- **Raw Events** — `f.events()` returns `list[Event]`
- **Failure Data** — `f.classify()` returns `list[dict]`

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

## Supported Frameworks

| Framework | Integration | Method |
|-----------|------------|--------|
| **Any** (manual) | `f.decision()`, `f.tool_call()`, `f.error()` | Direct API |
| **LangChain / LangGraph** | `f.langchain()` | Callback Handler (auto prompt drift) |
| **OpenAI Agents SDK** | `f.openai_agents()` | AgentHooks (auto model config capture) |
| **CrewAI** | `f.crewai()` | step_callback / task_callback |

## Event Types

| Type | When | Why It Matters |
|------|------|---------------|
| `decision` | Agent decides what to do next | Core of forensics — the *why* |
| `tool_call_start/end` | Tool execution | What tool, what input, what result |
| `llm_call_start/end` | LLM request/response | What was asked, what was answered |
| `error` | Something went wrong | Incident detection |
| `final_decision` | Agent produces final output | End of decision chain |
| `context_injection` | RAG/memory context injected | Which data influenced the decision |
| `prompt_state` | System prompt recorded | Baseline for drift detection |
| `prompt_drift` | System prompt changed | Instruction drift flagged |
| `guardrail_pass` | Action allowed by guardrail | Approval checkpoint |
| `guardrail_block` | Action blocked by guardrail | Prevention checkpoint |

## API Reference

### Core

| Method | Description |
|--------|-------------|
| `Forensics(session, agent, db_path)` | Initialize with session ID and agent name |
| `f.decision(action, input, reasoning)` | Record a decision |
| `f.tool_call(action, input, output)` | Record a tool call |
| `f.llm_call(input, output, model, temperature, seed)` | Record an LLM call with model config |
| `f.error(action, output, reasoning)` | Record an error |
| `f.finish(output, reasoning)` | Record final output |
| `f.context_injection(source, content, reasoning)` | Record RAG/memory context injection |
| `f.prompt_state(system_prompt)` | Record prompt state (auto drift detection) |
| `f.guardrail(intent, action, allowed, reason)` | Record guardrail checkpoint |

### Analysis

| Method | Description |
|--------|-------------|
| `f.report()` | Generate Markdown forensic report |
| `f.save_markdown(path)` | Save report as Markdown file |
| `f.save_pdf(path)` | Save report as PDF |
| `f.classify(session_id)` | Auto-classify failure patterns |
| `f.failure_stats(session_ids)` | Aggregate failures across sessions |
| `f.get_replay_config(session_id)` | Extract model config for replay |
| `f.replay_diff(original, replay)` | Compare original vs replayed session |
| `f.events()` | Get raw events for current session |
| `f.sessions()` | List all sessions |
| `f.dashboard(port)` | Launch web dashboard |

### Framework Integrations

| Method | Returns |
|--------|---------|
| `f.langchain()` | LangChain `BaseCallbackHandler` |
| `f.openai_agents()` | OpenAI Agents SDK `AgentHooks` |
| `f.crewai()` | CrewAI callback collection (`.step_callback`, `.task_callback`) |

## License

MIT
