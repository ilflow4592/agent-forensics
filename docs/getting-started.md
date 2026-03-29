# Getting Started

## Installation

=== "PyPI (recommended)"

    ```bash
    pip install agent-forensics
    ```

=== "With framework integration"

    ```bash
    pip install agent-forensics[langchain]       # LangChain / LangGraph
    pip install agent-forensics[openai-agents]   # OpenAI Agents SDK
    pip install agent-forensics[crewai]          # CrewAI
    pip install agent-forensics[all]             # Everything
    ```

=== "From source"

    ```bash
    git clone https://github.com/ilflow4592/agent-forensics.git
    cd agent-forensics
    pip install -e ".[all]"
    ```

## Your First Forensic Report

### 1. Initialize

```python
from agent_forensics import Forensics

f = Forensics(
    session="my-first-session",   # Unique session ID
    agent="my-agent",             # Agent name
    db_path="forensics.db",       # SQLite file (default)
)
```

### 2. Record Agent Actions

```python
# Agent decides to search for products
f.decision(
    "search_products",
    input={"query": "wireless mouse"},
    reasoning="User asked to find a wireless mouse",
)

# Agent calls a tool
f.tool_call(
    "search_api",
    input={"q": "wireless mouse"},
    output={"results": [{"name": "Logitech M750", "price": 45.00}]},
)

# Agent makes a purchase decision
f.guardrail(
    intent="buy cheapest mouse",
    action="purchase",
    allowed=True,
    reason="Price within $100 budget",
)

f.decision(
    "purchase",
    input={"product": "Logitech M750", "price": 45.00},
    reasoning="Cheapest option found, within budget",
)

# Agent finishes
f.finish("Ordered Logitech M750 for $45.00", reasoning="Purchase complete")
```

### 3. Generate Report

```python
# Print the full Markdown report
print(f.report())

# Save to files
f.save_markdown()   # → forensics-report-my-first-session.md
f.save_pdf()        # → forensics-report-my-first-session.pdf (requires [pdf] extra)
```

### 4. Check for Failures

```python
failures = f.classify()
if failures:
    for fail in failures:
        print(f"[{fail['severity']}] {fail['type']}: {fail['description']}")
else:
    print("No failures detected!")
```

### 5. Launch Dashboard

```python
f.dashboard(port=8080)  # Open http://localhost:8080
```

## Live Demo

Run the included demo to see a full scenario with failure detection:

```bash
# With Ollama (real LLM reasoning)
ollama pull mistral
python demo.py

# Without Ollama (preset responses)
python demo.py --no-llm
```

The demo runs two procurement sessions — one normal, one with silent failures — and shows how forensics catches what the agent hides.

## What's Next

- [API Reference](api-reference.md) — every method explained
- [Integrations](integrations.md) — auto-capture with LangChain, OpenAI, CrewAI
- [Failure Patterns](failure-patterns.md) — understand what each detection means
