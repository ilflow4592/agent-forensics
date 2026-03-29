# LangChain Community Integration PR

## Target Repo
`langchain-ai/langchain` → `libs/community/langchain_community/callbacks/`

## PR Title
`community: Add Agent Forensics callback handler for forensic reporting`

## PR Description

```markdown
## Description

Add `AgentForensicsCallbackHandler` — a callback handler that records all agent activity (decisions, tool calls, LLM interactions, errors) to an SQLite-backed event store for post-incident forensic analysis.

**Key features:**
- Records every decision point, tool call, and LLM interaction
- Auto-detects prompt drift between agent steps
- Captures model config (model, temperature, seed) for deterministic replay
- Auto-classifies 6 failure patterns (hallucinated tool output, missing approval, silent substitution, etc.)
- Generates forensic reports (Markdown/PDF) for EU AI Act Article 14 compliance

**Usage:**

```python
from langchain_community.callbacks import AgentForensicsCallbackHandler

handler = AgentForensicsCallbackHandler(
    session_id="order-123",
    agent_id="shopping-agent",
)

agent.invoke({"input": "..."}, config={"callbacks": [handler]})

# Generate forensic report
print(handler.report())

# Auto-classify failures
failures = handler.classify()
```

## Dependencies

Optional dependency: `agent-forensics` (`pip install agent-forensics`)

## Issue

N/A — new feature

## Twitter handle

N/A
```

## File to Add

Path: `libs/community/langchain_community/callbacks/agent_forensics.py`

See `agent_forensics_callback.py` in this directory for the implementation.
