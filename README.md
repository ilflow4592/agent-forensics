# Agent Forensics

**Black box for AI agents.** Capture every decision, generate forensic reports for EU AI Act compliance.

When an AI agent makes a wrong purchase, leaks data, or fails silently — you need to know **why**. Agent Forensics records every decision point, tool call, and LLM interaction, then reconstructs the causal chain when things go wrong.

## Why

- **EU AI Act** (Aug 2026): High-risk AI systems must provide decision traceability. Fines up to €35M or 7% of global revenue.
- **AI agents are already causing incidents**: Meta Sev-1 data leak (Mar 2026), unauthorized purchases, fabricated customer responses.
- **No existing tool** reconstructs the *why* behind agent failures. Monitoring tools watch in real-time. Forensics analyzes after the fact.

## Install

```bash
pip install agent-forensics              # Core only (manual recording)
pip install agent-forensics[langchain]   # + LangChain integration
pip install agent-forensics[openai-agents]  # + OpenAI Agents SDK
pip install agent-forensics[crewai]      # + CrewAI
pip install agent-forensics[all]         # Everything
```

## Quick Start

### Manual Recording (Framework-Agnostic)

```python
from agent_forensics import Forensics

f = Forensics(session="order-123", agent="shopping-agent")

f.decision("search_products", input={"query": "mouse"}, reasoning="User requested product search")
f.tool_call("search_api", input={"q": "mouse"}, output={"results": [...]})
f.error("purchase_failed", output={"reason": "Out of stock"})
f.finish("Could not complete purchase due to stock unavailability.")

print(f.report())       # Markdown forensic report
f.save_pdf()            # PDF report
f.dashboard(port=8080)  # Web dashboard at http://localhost:8080
```

### LangChain — One Line

```python
from agent_forensics import Forensics

f = Forensics(session="order-123")
agent.invoke({"input": "..."}, config={"callbacks": [f.langchain()]})
```

### OpenAI Agents SDK — One Line

```python
from agent_forensics import Forensics
from agents import Agent, Runner

f = Forensics(session="order-123")
agent = Agent(name="shopper", tools=[...], hooks=f.openai_agents())
result = await Runner.run(agent, "Buy a wireless mouse")
```

### CrewAI — Two Lines

```python
from agent_forensics import Forensics

f = Forensics(session="order-123")
hooks = f.crewai()
agent = Agent(role="shopper", step_callback=hooks.step_callback)
task = Task(description="...", agent=agent, callback=hooks.task_callback)
```

## What You Get

### Forensic Report

Every report includes:

- **Timeline** — Chronological record of all agent actions
- **Decision Chain** — Each decision with its reasoning
- **Incident Analysis** — Automatic error detection + root cause chain
- **Causal Chain** — `Decision → Tool Call → Result → Error` trace
- **Compliance Notes** — EU AI Act Article 14 (Human Oversight) support

### Web Dashboard

```bash
python -c "from agent_forensics import Forensics; Forensics(db_path='forensics.db').dashboard()"
```

Dark-themed dashboard with session selector, color-coded timeline, and causal chain visualization.

### Output Formats

- **Markdown** — `f.save_markdown()`
- **PDF** — `f.save_pdf()` (requires `pip install agent-forensics[pdf]`)
- **Web Dashboard** — `f.dashboard(port=8080)`
- **Raw Events** — `f.events()` returns `list[Event]`

## Architecture

```
Your Agent (any framework)
    │
    │  Callback / Hook (1 line of code)
    ▼
┌──────────────────────┐
│  Forensics Collector  │  Captures every LLM call, tool use, decision
├──────────────────────┤
│  Event Store (SQLite) │  Immutable event log
├──────────────────────┤
│  Report Generator     │  Markdown / PDF / Dashboard
└──────────────────────┘
```

## Supported Frameworks

| Framework | Integration | Method |
|-----------|------------|--------|
| **Any** (manual) | `f.decision()`, `f.tool_call()`, `f.error()` | Direct API |
| **LangChain / LangGraph** | `f.langchain()` | Callback Handler |
| **OpenAI Agents SDK** | `f.openai_agents()` | AgentHooks |
| **CrewAI** | `f.crewai()` | step_callback / task_callback |

## Event Types

| Type | When | Why It Matters |
|------|------|---------------|
| `decision` | Agent decides what to do next | Core of forensics — the *why* |
| `tool_call_start` | Tool execution begins | What tool, what input |
| `tool_call_end` | Tool returns result | What came back |
| `llm_call_start` | LLM request sent | What was asked |
| `llm_call_end` | LLM response received | What was answered |
| `error` | Something went wrong | Incident detection |
| `final_decision` | Agent produces final output | End of decision chain |

## License

MIT
