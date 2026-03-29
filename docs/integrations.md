# Framework Integrations

Agent Forensics provides one-line integrations for popular agent frameworks. Each integration auto-captures decisions, tool calls, LLM interactions, and errors — no manual recording needed.

## Supported Frameworks

| Framework | Integration | Auto-captures |
|-----------|------------|---------------|
| [LangChain / LangGraph](integrations/langchain.md) | Callback Handler | LLM calls, tools, agent actions, prompt drift |
| [OpenAI Agents SDK](integrations/openai-agents.md) | AgentHooks | Agent lifecycle, tools, LLM calls with model config |
| [CrewAI](integrations/crewai.md) | Step/Task callbacks | Agent steps, task completion, errors |
| **Any framework** | [Manual API](api-reference.md) | Whatever you record |

## How It Works

All integrations follow the same pattern:

1. Create a `Forensics` instance
2. Get a framework-specific handler (one line)
3. Attach it to your agent
4. Run your agent normally — forensics are captured automatically

```python
from agent_forensics import Forensics

f = Forensics(session="my-session", agent="my-agent")

# Choose your framework:
handler = f.langchain()       # LangChain
hooks = f.openai_agents()     # OpenAI Agents SDK
callbacks = f.crewai()        # CrewAI

# After the agent runs:
print(f.report())
failures = f.classify()
```

## Manual + Auto Hybrid

You can combine auto-capture with manual recording. This is useful for adding context that the framework doesn't capture:

```python
f = Forensics(session="hybrid")

# Auto-capture via LangChain
agent.invoke({"input": "..."}, config={"callbacks": [f.langchain()]})

# Manually add context the framework missed
f.context_injection("internal_db", content={"policy": "max $500"})
f.guardrail(intent="buy item", action="purchase", allowed=True, reason="Within policy")
```
