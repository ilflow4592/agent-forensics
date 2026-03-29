# OpenAI Agents SDK Integration

Auto-capture agent activity through OpenAI's AgentHooks system.

## Installation

```bash
pip install agent-forensics[openai-agents]
```

Requires `openai-agents >= 0.1`.

## Usage

```python
from agent_forensics import Forensics
from agents import Agent, Runner, function_tool

f = Forensics(session="openai-demo", agent="shopping-agent")

@function_tool
def search_products(query: str) -> str:
    """Search the product catalog."""
    return '{"results": [{"name": "Mouse A", "price": 29.99}]}'

agent = Agent(
    name="shopper",
    instructions="You help users buy products.",
    tools=[search_products],
    hooks=f.openai_agents(),  # One line!
)

result = await Runner.run(agent, "Buy a wireless mouse")
print(f.report())
```

## What Gets Captured

| Event | Source | Details |
|-------|--------|---------|
| `decision` | `on_start` | Agent started processing |
| `tool_call_start/end` | `on_tool_start` / `on_tool_end` | Tool name, args, result |
| `llm_call_start/end` | `on_llm_start` / `on_llm_end` | Messages, model config (name, temperature, seed) |
| `final_decision` | `on_end` | Agent's final output |
| `error` | `on_error` | Error details |

## Model Config Capture

The OpenAI Agents integration automatically captures model configuration (model name, temperature, seed) from each LLM call. This enables deterministic replay:

```python
config = f.get_replay_config("openai-demo")
print(config["model_config"])
# {'model': 'gpt-4o', 'temperature': 0, 'seed': 42}
```

## Full Example

```python
import asyncio
from agent_forensics import Forensics
from agents import Agent, Runner, function_tool

@function_tool
def search(query: str) -> str:
    """Search products."""
    return '[{"name": "Logitech M750", "price": 45}]'

@function_tool
def purchase(product: str) -> str:
    """Purchase a product."""
    return '{"status": "confirmed", "order_id": "ORD-001"}'

async def main():
    f = Forensics(session="order-001", agent="buyer")

    agent = Agent(
        name="buyer",
        instructions="Buy the cheapest product matching the user's request.",
        tools=[search, purchase],
        hooks=f.openai_agents(),
    )

    result = await Runner.run(agent, "I need a wireless mouse")
    print(result.final_output)

    # Analysis
    print(f.report())
    f.save_markdown()

asyncio.run(main())
```
