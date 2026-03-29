# API Reference

## Forensics

The main interface. All functionality is accessed through this class.

```python
from agent_forensics import Forensics

f = Forensics(
    session="session-id",       # Unique session identifier
    agent="agent-name",         # Agent name for the trace
    db_path="forensics.db",     # Path to SQLite database
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session` | `str` | `"default"` | Session ID. Use unique IDs to isolate traces. |
| `agent` | `str` | `"default-agent"` | Agent name recorded with every event. |
| `db_path` | `str` | `"forensics.db"` | Path to the SQLite database file. Created if it doesn't exist. |

---

## Recording Methods

### `decision()`

Record when the agent makes a decision.

```python
f.decision(
    action="search_products",
    input={"query": "wireless mouse"},
    reasoning="User requested product search",
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | `str` | Yes | What the agent decided to do |
| `input` | `dict` | No | Input data that informed the decision |
| `reasoning` | `str` | No | Why the agent made this decision |

**Returns:** `str` — event ID

---

### `tool_call()`

Record a tool execution. Creates two events: `tool_call_start` and `tool_call_end`.

```python
f.tool_call(
    action="search_api",
    input={"q": "wireless mouse"},
    output={"results": [{"name": "Mouse A", "price": 29.99}]},
    reasoning="Searching product catalog",
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | `str` | Yes | Tool name |
| `input` | `dict` | No | Tool input parameters |
| `output` | `dict` | No | Tool output / result |
| `reasoning` | `str` | No | Why this tool was called |

**Returns:** `str` — event ID of the `tool_call_end` event

---

### `llm_call()`

Record an LLM call with model configuration for deterministic replay.

```python
f.llm_call(
    input={"messages": [{"role": "user", "content": "Find a mouse"}]},
    output="I found several options...",
    model="gpt-4o",
    temperature=0.0,
    seed=42,
    reasoning="Initial product search query",
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `input` | `dict` | No | What was sent to the LLM |
| `output` | `str` | No | What the LLM returned |
| `model` | `str` | No | Model name (e.g., `"gpt-4o"`, `"claude-sonnet-4-20250514"`) |
| `temperature` | `float` | No | Temperature setting |
| `seed` | `int` | No | Random seed (if supported) |
| `reasoning` | `str` | No | Why this LLM call was made |

**Returns:** `str` — event ID

!!! tip "Model config for replay"
    The `model`, `temperature`, and `seed` parameters are stored as `_model_config` in the event data. Use `get_replay_config()` to extract them later.

---

### `error()`

Record an error or incident.

```python
f.error(
    action="purchase_failed",
    output={"reason": "Out of stock", "code": 404},
    reasoning="API returned stock unavailable",
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | `str` | Yes | What failed |
| `output` | `dict` | No | Error details |
| `reasoning` | `str` | No | Error context |

---

### `finish()`

Record the agent's final output.

```python
f.finish(
    output="Ordered Logitech M750 for $45",
    reasoning="Purchase completed successfully",
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `output` | `str` | No | Final result text |
| `reasoning` | `str` | No | Why this is the final answer |

---

### `guardrail()`

Record a guardrail checkpoint — was a critical action allowed or blocked?

```python
f.guardrail(
    intent="check price",
    action="purchase item",
    allowed=True,
    reason="Price within approved budget",
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `intent` | `str` | Yes | What the agent intended to do |
| `action` | `str` | Yes | What the agent actually did or tried |
| `allowed` | `bool` | Yes | Whether the action was permitted |
| `reason` | `str` | No | Why it was allowed or blocked |

!!! warning "Missing guardrails"
    Critical actions (purchase, delete, send) without a preceding guardrail check trigger the `MISSING_APPROVAL` failure pattern.

---

### `context_injection()`

Record when external context is injected (RAG chunks, memory, retrieved docs).

```python
f.context_injection(
    source="vector_db",
    content={
        "document": "refund_policy.md",
        "similarity_score": 0.92,
    },
    reasoning="RAG retrieval for refund question",
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source` | `str` | Yes | Where the context came from |
| `content` | `dict` | No | The actual context data |
| `reasoning` | `str` | No | Why this context was injected |

!!! tip "Similarity scores"
    Include `similarity_score` in the `content` dict. Scores below 0.7 trigger the `RETRIEVAL_MISMATCH` failure pattern.

---

### `prompt_state()`

Record the current system prompt. Automatically detects drift from the previous state.

```python
f.prompt_state(
    system_prompt="You are a helpful shopping assistant.",
    metadata={"version": 2},
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `system_prompt` | `str` | Yes | Current system prompt text |
| `metadata` | `dict` | No | Additional info (version, source, etc.) |

When the prompt changes from the previous call, the event type becomes `prompt_drift` instead of `prompt_state`, and a diff is computed automatically.

---

### `record()`

Record a generic event (for custom event types).

```python
f.record(
    event_type="custom_check",
    action="validate_output",
    input={"schema": "order"},
    output={"valid": True},
    reasoning="Output validation step",
)
```

---

## Analysis Methods

### `report()`

Generate the full Markdown forensic report.

```python
markdown = f.report()
print(markdown)
```

**Returns:** `str` — complete Markdown report

---

### `save_markdown()` / `save_pdf()`

Save the report to a file.

```python
f.save_markdown("./reports")   # → ./reports/forensics-report-session-id.md
f.save_pdf("./reports")        # → ./reports/forensics-report-session-id.pdf
```

`save_pdf()` requires the `pdf` extra: `pip install agent-forensics[pdf]`

---

### `classify()`

Auto-classify failure patterns in a session trace.

```python
failures = f.classify()                    # Current session
failures = f.classify(session_id="other")  # Specific session
```

**Returns:** `list[dict]` — each dict contains:

```python
{
    "type": "MISSING_APPROVAL",       # Failure pattern name
    "severity": "HIGH",               # HIGH / MEDIUM / LOW
    "description": "Critical action...",
    "evidence": {"action": "purchase", ...},
    "step": 5,                        # Position in timeline
}
```

See [Failure Patterns](failure-patterns.md) for all pattern types.

---

### `failure_stats()`

Aggregate failure patterns across multiple sessions.

```python
stats = f.failure_stats()                              # All sessions
stats = f.failure_stats(session_ids=["s1", "s2"])      # Specific sessions
```

**Returns:**

```python
{
    "total_failures": 12,
    "by_type": {
        "MISSING_APPROVAL": {"count": 5, "description": "...", "severities": [...]},
        ...
    },
    "by_severity": {"HIGH": 7, "MEDIUM": 4, "LOW": 1},
}
```

---

### `get_replay_config()`

Extract model config and step sequence from a recorded session.

```python
config = f.get_replay_config("session-123")
```

**Returns:**

```python
{
    "session_id": "session-123",
    "model_config": {"model": "gpt-4o", "temperature": 0, "seed": 42},
    "steps": [{"type": "decision", "action": "...", ...}, ...],
    "tool_responses": {"tool_result": {...}},
    "total_events": 15,
}
```

---

### `replay_diff()`

Compare two sessions (original vs replay) and return differences.

```python
diff = f.replay_diff("original-session", "replay-session")
```

**Returns:**

```python
{
    "original_session": "original-session",
    "replay_session": "replay-session",
    "matching": False,
    "divergences": [
        {"step": 3, "type": "diverged", "original": {...}, "replay": {...}},
    ],
}
```

Divergence types: `diverged`, `extra_in_replay`, `missing_in_replay`

---

## Query Methods

### `events()`

Return all events for the current session.

```python
events = f.events()
for e in events:
    print(f"[{e.event_type}] {e.action}")
```

**Returns:** `list[Event]`

### `sessions()`

Return all session IDs in the database.

```python
print(f.sessions())  # ['order-123', 'order-456']
```

---

## Integration Methods

### `langchain()`

Return a LangChain callback handler.

```python
handler = f.langchain()
agent.invoke({"input": "..."}, config={"callbacks": [handler]})
```

### `openai_agents()`

Return OpenAI Agents SDK hooks.

```python
hooks = f.openai_agents()
agent = Agent(name="shopper", hooks=hooks)
```

### `crewai()`

Return CrewAI callback collection.

```python
hooks = f.crewai()
agent = Agent(role="...", step_callback=hooks.step_callback)
```

---

## Event

The `Event` dataclass represents a single recorded event.

```python
from agent_forensics import Event
```

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `str` | ISO format UTC timestamp |
| `event_type` | `str` | Event type (decision, tool_call_start, error, etc.) |
| `agent_id` | `str` | Agent name |
| `action` | `str` | What happened |
| `input_data` | `dict` | Input data |
| `output_data` | `dict` | Output data |
| `reasoning` | `str` | Why this event occurred |
| `session_id` | `str` | Session this event belongs to |
| `event_id` | `str` | Unique event identifier |

## EventStore

Low-level access to the SQLite event store.

```python
from agent_forensics import EventStore

store = EventStore("forensics.db")
events = store.get_session_events("session-123")
sessions = store.get_all_sessions()
```
