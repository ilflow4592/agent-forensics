# Awesome List Submissions

## 1. awesome-langchain (kyrolabs/awesome-langchain)

**Section:** Tools / Monitoring & Observability (or similar)

**Entry to add:**

```markdown
- [Agent Forensics](https://github.com/ilflow4592/agent-forensics) - Black box for AI agents. Capture every decision, auto-detect 6 failure patterns, generate forensic reports for EU AI Act compliance. One-line LangChain integration via callback handler. ![GitHub Repo stars](https://img.shields.io/github/stars/ilflow4592/agent-forensics)
```

**PR title:** `Add Agent Forensics — forensic reporting & failure detection for LangChain agents`

**PR body:**

```markdown
## What is Agent Forensics?

Black box for AI agents — records every decision, tool call, and LLM interaction, then auto-classifies 6 failure patterns (hallucinated tool output, missing approval, silent substitution, prompt drift, repeated failure, retrieval mismatch).

**LangChain integration:** One-line callback handler that auto-captures all agent activity including prompt drift detection.

```python
from agent_forensics import Forensics

f = Forensics(session="order-123")
agent.invoke({"input": "..."}, config={"callbacks": [f.langchain()]})
print(f.report())
```

- PyPI: `pip install agent-forensics[langchain]`
- GitHub: https://github.com/ilflow4592/agent-forensics
- Docs: https://ilflow4592.github.io/agent-forensics/
```

---

## 2. awesome-llm (Hannibal046/Awesome-LLM)

**Section:** Tools (or LLM Agent Tools)

**Entry to add:**

```markdown
- [Agent Forensics](https://github.com/ilflow4592/agent-forensics) - Black box for AI agents — forensic reports, failure auto-classification, EU AI Act compliance. Supports LangChain, OpenAI Agents SDK, CrewAI.
```

**PR title:** `Add Agent Forensics to Tools section`

---

## 3. awesome-ai-agents (e2b-dev/awesome-ai-agents)

**Section:** Frameworks & Tools (or Observability)

**Entry to add:**

```markdown
### Agent Forensics
Black box for AI agents. Captures every decision, auto-detects 6 failure patterns, generates forensic reports for EU AI Act compliance. Framework-agnostic with one-line integrations for LangChain, OpenAI Agents SDK, and CrewAI.

- **GitHub:** https://github.com/ilflow4592/agent-forensics
- **PyPI:** `pip install agent-forensics`
```

**PR title:** `Add Agent Forensics — forensic reporting & failure classification for AI agents`
