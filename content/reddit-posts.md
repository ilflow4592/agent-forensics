# Reddit Posts

## Post 1: r/artificial

**Title:** I built an open-source "black box" for AI agents — it records every decision so you can figure out why an agent did what it did

**Body:**

I've been working with AI agents (LangChain, OpenAI Agents SDK, CrewAI) and kept running into the same problem: when an agent does something wrong, nobody can explain *why* it made that decision.

A few recent examples that pushed me to build this:

- Meta's Sev-1 incident (March 2026): an internal AI agent leaked company data to unauthorized engineers. The team couldn't fully reconstruct the agent's decision path.
- A shopping agent was asked to check egg prices and instead *purchased eggs* without user consent.
- Customer support bots giving completely fabricated explanations to real customers.

The common thread: **no audit trail of agent decisions**.

So I built [Agent Forensics](https://github.com/ilflow4592/agent-forensics) — think airplane black box, but for AI agents. You add one line of code and it captures every decision, tool call, and LLM interaction. When something goes wrong, it reconstructs the causal chain:

```
[DECISION] search_products("Apple Magic Mouse")
  → [TOOL] search_api → ERROR: not found

[DECISION] search_products("Apple wireless mouse")
  → [TOOL] search_api → OK: 3 products found

[DECISION] compare_prices → cheapest is Logitech M750

[DECISION] purchase("Logitech M750") → SUCCESS

[FINAL] "Purchased Logitech M750 for $45"
```

The user asked for an Apple Magic Mouse. The agent bought a completely different product. The forensic trail shows exactly where and why the substitution happened.

**Why this matters now:**

EU AI Act enforcement starts August 2026. High-risk AI systems need decision traceability. Fines up to €35M or 7% of global revenue. "We didn't track it" isn't a valid defense.

**How to use it:**

```bash
pip install agent-forensics[all]
```

```python
from agent_forensics import Forensics

f = Forensics(session="order-123")

# Step 1: Record — choose your framework
agent.invoke(..., config={"callbacks": [f.langchain()]})   # LangChain
# or: Agent(hooks=f.openai_agents())                       # OpenAI Agents SDK
# or: f.decision("search", input={...}, reasoning="...")   # Any framework

# Step 2: Get reports
f.save_markdown()       # → forensics-report-order-123.md
f.save_pdf()            # → forensics-report-order-123.pdf

# Step 3: Visual dashboard
f.dashboard(port=8080)  # → http://localhost:8080
```

- Pure Python, SQLite storage, no cloud dependency
- One-line integration with LangChain, OpenAI Agents SDK, CrewAI
- Also works with any custom agent via manual API
- MIT licensed, fully open source

GitHub: https://github.com/ilflow4592/agent-forensics
PyPI: `pip install agent-forensics`

Would love feedback. What would make this actually useful for your agents?

---

## Post 2: r/MachineLearning

**Title:** [P] Agent Forensics — open-source decision tracing for AI agents (LangChain, OpenAI Agents SDK, CrewAI)

**Body:**

Sharing a project I've been working on: **Agent Forensics**, an open-source library that captures AI agent decision paths for post-incident analysis.

**Problem:** Current observability tools (Arize, Langfuse, etc.) focus on real-time monitoring — "is the agent working right now?" But after an incident, the question is different: "why did the agent make *this specific decision* at *this specific moment*?" That's a forensics question, and there's no good tooling for it.

**Approach:**

The library hooks into agent frameworks via their native callback/hook mechanisms:

- **LangChain/LangGraph**: `BaseCallbackHandler` — captures `on_chat_model_start`, `on_llm_end` (including tool_calls from AIMessage), `on_tool_start/end`
- **OpenAI Agents SDK**: `AgentHooks` — captures `on_start`, `on_llm_start/end`, `on_tool_start/end`, `on_handoff` (multi-agent)
- **CrewAI**: `step_callback` + `task_callback`
- **Framework-agnostic**: manual `decision()`, `tool_call()`, `error()` API

All events are stored in SQLite with session isolation. The report generator reconstructs:

1. **Timeline** — chronological event sequence
2. **Decision chain** — each decision point with its reasoning
3. **Causal chain** — linked sequence showing how decision A led to tool call B, which returned result C, causing decision D
4. **Incident detection** — automatic identification of error events and failed tool calls

**Key design decision:** Extracting "decisions" from different frameworks is non-trivial. LangChain buries tool call decisions inside `AIMessage.tool_calls`. OpenAI Agents SDK exposes them cleanly via `on_tool_start`. CrewAI passes them through `step_callback` as `AgentAction` objects. The abstraction layer normalizes all of these into a common `Event` schema.

**Full workflow:**

```bash
pip install agent-forensics[all]
```

```python
from agent_forensics import Forensics

f = Forensics(session="order-123")

# 1. Record (auto-capture via framework hooks)
agent.invoke(..., config={"callbacks": [f.langchain()]})

# 2. Analyze
print(f.report())          # Full Markdown forensic report
events = f.events()        # Raw event data for custom analysis

# 3. Export
f.save_markdown()          # → forensics-report-order-123.md
f.save_pdf()               # → forensics-report-order-123.pdf

# 4. Visualize
f.dashboard(port=8080)     # Web UI with timeline + causal chain
```

Reports include timeline tables, decision chains with reasoning, causal chain analysis, and EU AI Act Article 14 compliance notes. The built-in web dashboard (pure Python http.server, no dependencies) provides session selection, color-coded timelines, and incident visualization.

**Motivation:** EU AI Act (Aug 2026) requires decision traceability for high-risk AI. But even without regulation, if you're running agents in production, you need to understand why they fail.

GitHub: https://github.com/ilflow4592/agent-forensics
PyPI: `pip install agent-forensics`

Feedback welcome — especially from anyone running agents in production at scale. What's missing?

---

## Post 3: r/LangChain

**Title:** Built a forensics tool that captures every decision your LangChain agent makes — one callback handler

**Body:**

I kept hitting the same problem: my LangChain agent would do something unexpected, and I'd have no idea why. `verbose=True` shows what happened during execution, but after the fact? Nothing.

So I built a callback handler that records every decision into a SQLite database and generates forensic reports.

**Setup:**

```bash
pip install agent-forensics[langchain]
```

**How it works:**

```python
from agent_forensics import Forensics

f = Forensics(session="order-123")

# Just add the callback — that's it
result = agent.invoke(
    {"input": "Buy me a wireless mouse"},
    config={"callbacks": [f.langchain()]}
)

# Generate reports
print(f.report())          # Print Markdown report to console
f.save_markdown()          # Save as ./forensics-report-order-123.md
f.save_pdf()               # Save as ./forensics-report-order-123.pdf

# Or launch the visual dashboard
f.dashboard(port=8080)     # http://localhost:8080
```

The callback captures:

| Event | What's recorded |
|-------|----------------|
| `on_chat_model_start` | Messages sent to LLM |
| `on_llm_end` | LLM response + tool_calls (parsed from AIMessage) |
| `on_tool_start` | Which tool, what input |
| `on_tool_end` | Tool result |
| Errors | Any failures with context |

The tricky part was extracting **decisions** from LangGraph's ReAct agent. When the LLM decides to call a tool, it doesn't fire `on_agent_action` (that's the old AgentExecutor pattern). Instead, the decision is buried inside `AIMessage.tool_calls` in the `on_llm_end` response. The callback handler parses these out and records them as explicit decision events.

**Output example (causal chain from an actual incident):**

```
[DECISION] search_products("Apple Magic Mouse")
  → [TOOL] search_api → ERROR: not found

[DECISION] search_products("Apple wireless mouse")
  → [TOOL] search_api → OK: found 3 products

[DECISION] compare_prices → Logitech M750 cheapest

[DECISION] purchase("Logitech M750") → SUCCESS

[FINAL] "Purchased Logitech M750"
  ← User asked for Apple Magic Mouse. Agent substituted without asking.
```

The web dashboard gives you a visual timeline with color-coded events (blue for decisions, yellow for tool calls, red for errors) and a causal chain view for incidents.

You can also access raw events programmatically:

```python
for event in f.events():
    print(f"[{event.event_type}] {event.action} — {event.reasoning}")
```

Works with LangGraph `create_react_agent` and the older `AgentExecutor` pattern.

GitHub: https://github.com/ilflow4592/agent-forensics

`pip install agent-forensics[langchain]`

What kind of agent failures have you run into that something like this would've helped debug?

---

## Post 4: r/OpenAI

**Title:** Open-source tool to trace every decision your OpenAI agent makes — plugs into the Agents SDK via hooks

**Body:**

If you're using the OpenAI Agents SDK, here's something I built that might be useful: a forensics library that records every decision your agent makes so you can reconstruct what happened after the fact.

**Install:**

```bash
pip install agent-forensics[openai-agents]
```

**Full workflow:**

```python
from agent_forensics import Forensics
from agents import Agent, Runner

f = Forensics(session="order-123")

# Step 1: Attach hooks — captures everything automatically
agent = Agent(
    name="shopping-agent",
    instructions="...",
    tools=[search_products, purchase],
    hooks=f.openai_agents(),
)

result = await Runner.run(agent, "Buy a wireless mouse")

# Step 2: Get the forensic report
print(f.report())          # Full Markdown report to console
f.save_markdown()          # → forensics-report-order-123.md
f.save_pdf()               # → forensics-report-order-123.pdf

# Step 3: Visual dashboard
f.dashboard(port=8080)     # → http://localhost:8080
```

**What it captures via AgentHooks:**

- `on_start` / `on_end` — agent lifecycle
- `on_llm_start` / `on_llm_end` — every LLM call with inputs and tool_calls
- `on_tool_start` / `on_tool_end` — every tool execution with results
- `on_handoff` — multi-agent handoffs (which agent passed work to which)

That last one is interesting for multi-agent setups. If Agent A hands off to Agent B, and Agent B makes a mistake, you can trace it back through the handoff chain.

**What the report looks like:**

You get a timeline of every event, a decision chain showing each choice the agent made with its reasoning, and — if an incident occurred — a causal chain tracing the root cause. Reports come in Markdown, PDF, or via a built-in web dashboard with color-coded timelines and incident visualization.

You can also query raw events:

```python
for event in f.events():
    print(f"[{event.event_type}] {event.action}")

print(f.sessions())  # List all recorded sessions
```

Everything is stored in a local SQLite file. No cloud, no external dependencies.

Built this because EU AI Act enforcement starts in August and requires decision traceability for AI systems. But honestly, even without regulation, if your agent is making purchases or handling customer data, you want to know why it did what it did.

GitHub: https://github.com/ilflow4592/agent-forensics

`pip install agent-forensics[openai-agents]`

---

## Posting Strategy

| Subreddit | Post | Best Time (PT) | Notes |
|-----------|------|----------------|-------|
| r/artificial (~2.5M) | Post 1 | Tuesday 9-11 AM | Broadest audience, lead with the problem |
| r/MachineLearning (~3M) | Post 2 | Wednesday 9-11 AM | Technical audience, use [P] tag |
| r/LangChain (~80K) | Post 3 | Thursday 9-11 AM | Targeted, LangChain-specific value |
| r/OpenAI (~1.5M) | Post 4 | Friday 9-11 AM | Agents SDK specific |

**Rules:**
- Space posts 1-2 days apart (don't spam)
- Reply to every comment within a few hours
- Don't cross-post the same content
- Each post is tailored to the subreddit's audience
- Never be defensive about feedback — thank people and ask follow-ups
