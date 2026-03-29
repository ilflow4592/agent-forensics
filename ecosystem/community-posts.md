# Community Posts

Ready-to-use posts for community engagement.

---

## LangChain Discord — #show-and-tell

```
Hey everyone! I built Agent Forensics — a "black box" for LangChain agents.

It records every decision, tool call, and LLM interaction, then auto-detects 6 failure patterns (hallucinated tool output, missing approval, silent substitution, prompt drift, repeated failure, retrieval mismatch).

One-line integration:

from agent_forensics import Forensics
f = Forensics(session="order-123")
agent.invoke({"input": "..."}, config={"callbacks": [f.langchain()]})
print(f.report())  # Full forensic report

Why I built it: EU AI Act requires decision traceability for high-risk AI by Aug 2026, and I kept running into agent failures that were impossible to debug after the fact.

GitHub: https://github.com/ilflow4592/agent-forensics
PyPI: pip install agent-forensics[langchain]
Docs: https://ilflow4592.github.io/agent-forensics/

Would love feedback, especially on what failure patterns you've seen in your agents!
```

---

## r/LocalLLaMA (Ollama angle)

**Title:** `I built a "black box" for AI agents — includes a live demo with Ollama + Mistral`

```
I built Agent Forensics — a forensic analysis tool for AI agents. Think of it as a flight recorder that captures every decision, tool call, and LLM interaction, then auto-classifies what went wrong.

The included demo ("The Silent $47K Mistake") runs two identical procurement requests through an Ollama + Mistral agent:
- Run 1: Everything works fine
- Run 2: The agent silently substitutes the product, skips approval, and reports "success"

Without forensics, Run 2 looks like a win ("saved $14,100!"). With forensics, 5 failure patterns are detected.

python demo.py  # requires: ollama pull mistral

No API keys needed — everything runs locally.

GitHub: https://github.com/ilflow4592/agent-forensics
```

---

## CrewAI GitHub Discussions

**Title:** `Agent Forensics — forensic reporting for CrewAI agents`

```
Hi! I built Agent Forensics, a tool that records agent decisions and auto-classifies failures. It has a CrewAI integration:

from agent_forensics import Forensics

f = Forensics(session="crew-task-001")
hooks = f.crewai()

agent = Agent(
    role="researcher",
    step_callback=hooks.step_callback,
)
task = Task(
    description="...",
    agent=agent,
    callback=hooks.task_callback,
)

crew = Crew(agents=[agent], tasks=[task])
crew.kickoff()

# After execution:
print(f.report())       # Timeline + decision chain + causal analysis
failures = f.classify()  # Auto-detect 6 failure patterns

Useful for debugging multi-agent workflows and EU AI Act compliance.

GitHub: https://github.com/ilflow4592/agent-forensics
Docs: https://ilflow4592.github.io/agent-forensics/integrations/crewai/
```

---

## OpenAI Community Forums

**Title:** `Agent Forensics — forensic reporting for OpenAI Agents SDK`

```
Built a forensic analysis tool for AI agents that works with the OpenAI Agents SDK.

One-line integration:

agent = Agent(
    name="shopper",
    tools=[...],
    hooks=f.openai_agents(),  # captures everything
)

After the agent runs, you get:
- Full timeline of decisions, tool calls, and LLM interactions
- Auto-detection of 6 failure patterns
- Deterministic replay (model config capture)
- Forensic reports for compliance

GitHub: https://github.com/ilflow4592/agent-forensics
PyPI: pip install agent-forensics[openai-agents]
```
