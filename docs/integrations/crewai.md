# CrewAI Integration

Capture agent steps and task completions through CrewAI's callback system.

## Installation

```bash
pip install agent-forensics[crewai]
```

Requires `crewai >= 0.80`.

## Usage

```python
from agent_forensics import Forensics
from crewai import Agent, Task, Crew
from crewai_tools import tool

f = Forensics(session="crewai-demo", agent="shopping-crew")
hooks = f.crewai()

agent = Agent(
    role="shopper",
    goal="Find and buy the best product",
    backstory="You are an expert online shopper.",
    step_callback=hooks.step_callback,  # Capture every step
)

task = Task(
    description="Buy a wireless mouse under $50",
    agent=agent,
    callback=hooks.task_callback,  # Capture task completion
)

crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()

print(f.report())
```

## What Gets Captured

| Event | Source | Details |
|-------|--------|---------|
| `decision` | `step_callback` | Each agent reasoning step |
| `tool_call_start/end` | `step_callback` | Tool usage within steps |
| `final_decision` | `task_callback` | Task completion result |
| `error` | `step_callback` | Step errors |

## Callbacks

The `crewai()` method returns an object with two callbacks:

| Callback | Attach To | Purpose |
|----------|-----------|---------|
| `hooks.step_callback` | `Agent(step_callback=...)` | Records every agent step |
| `hooks.task_callback` | `Task(callback=...)` | Records task completion |

## Full Example

```python
from agent_forensics import Forensics
from crewai import Agent, Task, Crew
from crewai_tools import tool

@tool("search_products")
def search_products(query: str) -> str:
    """Search the product catalog for items matching the query."""
    return '[{"name": "Logitech M750", "price": 45}]'

@tool("purchase_product")
def purchase_product(product: str) -> str:
    """Purchase a product by name."""
    return '{"status": "confirmed", "order_id": "ORD-001"}'

f = Forensics(session="crew-shopping", agent="shopping-crew")
hooks = f.crewai()

shopper = Agent(
    role="Online Shopper",
    goal="Find and purchase the best product within budget",
    backstory="Expert online shopper with 10 years of experience.",
    tools=[search_products, purchase_product],
    step_callback=hooks.step_callback,
)

buy_task = Task(
    description="Find a wireless mouse under $50 and purchase it.",
    expected_output="Confirmation of purchase with order ID.",
    agent=shopper,
    callback=hooks.task_callback,
)

crew = Crew(agents=[shopper], tasks=[buy_task], verbose=True)
result = crew.kickoff()

# Analysis
print(f"Events recorded: {len(f.events())}")
print(f.report())
f.save_markdown()
```
