# LangChain Integration

Auto-capture all agent activity through LangChain's callback system.

## Installation

```bash
pip install agent-forensics[langchain]
```

Requires `langchain-core >= 0.3`.

## Usage

```python
from agent_forensics import Forensics
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

f = Forensics(session="langchain-demo", agent="react-agent")

# Create your agent as usual
llm = ChatOllama(model="mistral")
agent = create_react_agent(llm, tools=[...])

# Add forensics with one line
result = agent.invoke(
    {"messages": [("user", "Find me a wireless mouse")]},
    config={"callbacks": [f.langchain()]},
)

# Generate report
print(f.report())
```

## What Gets Captured

| Event | Source | Details |
|-------|--------|---------|
| `llm_call_start/end` | `on_chat_model_start` / `on_chat_model_end` | Full message history, model response |
| `tool_call_start/end` | `on_tool_start` / `on_tool_end` | Tool name, input, output |
| `decision` | `on_agent_action` | Agent's chosen action + reasoning |
| `final_decision` | `on_agent_finish` | Final output |
| `error` | `on_llm_error` / `on_tool_error` | Error details |
| `prompt_drift` | Automatic | System prompt changes between steps |

## Prompt Drift Detection

The LangChain integration automatically tracks system prompt changes. If the system message in the LLM call differs from the previous call, a `prompt_drift` event is recorded.

```python
# No manual prompt_state() calls needed!
# The callback handler extracts system messages from each LLM call
```

## Full Example

```python
from agent_forensics import Forensics
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

@tool
def search_products(query: str) -> str:
    """Search the product catalog."""
    return '{"results": [{"name": "Logitech M750", "price": 45}]}'

@tool
def purchase(product: str, quantity: int) -> str:
    """Purchase a product."""
    return f'{{"status": "confirmed", "product": "{product}", "qty": {quantity}}}'

f = Forensics(session="shopping-session", agent="shopping-agent")

llm = ChatOllama(model="mistral")
agent = create_react_agent(llm, tools=[search_products, purchase])

result = agent.invoke(
    {"messages": [("user", "Buy the cheapest wireless mouse")]},
    config={"callbacks": [f.langchain()]},
)

# Forensic analysis
print(f"Events: {len(f.events())}")
print(f.report())

failures = f.classify()
for fail in failures:
    print(f"[{fail['severity']}] {fail['type']}: {fail['description']}")
```
