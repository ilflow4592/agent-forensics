"""
OpenAI Agents SDK integration example.

Usage:
    export OPENAI_API_KEY=sk-...
    python example_openai_agents.py
"""

import asyncio
import json
import sys
sys.path.insert(0, "..")

from agents import Agent, Runner, function_tool
from agent_forensics import Forensics


# -- Tool definitions --

@function_tool
def search_products(query: str) -> str:
    """Search for products."""
    products = [
        {"name": "Logitech M750", "price": 45000, "stock": 5},
        {"name": "Apple Magic Mouse", "price": 129000, "stock": 0},
        {"name": "Razer DeathAdder", "price": 69000, "stock": 12},
    ]
    return json.dumps(products, ensure_ascii=False)


@function_tool
def purchase(product_name: str) -> str:
    """Purchase a product."""
    if "magic" in product_name.lower():
        return json.dumps({"error": "PURCHASE_FAILED", "reason": "Out of stock"})
    return json.dumps({"status": "SUCCESS", "product": product_name, "price": 45000})


async def main():
    # 1. Initialize Forensics
    f = Forensics(session="openai-agents-demo", agent="shopping-agent")

    # 2. Create agent — connect forensics hooks
    agent = Agent(
        name="shopping-agent",
        instructions=(
            "You are a shopping assistant. "
            "Search for products, then purchase the cheapest one."
        ),
        tools=[search_products, purchase],
        hooks=f.openai_agents(),  # This one line auto-records all actions
    )

    # 3. Execute
    result = await Runner.run(agent, "Buy me a wireless mouse, the cheapest one please")
    print(f"Result: {result.final_output}")

    # 4. Report
    print(f"\nEvents captured: {len(f.events())}")
    f.save_markdown()
    f.save_pdf()
    print(f.report())


if __name__ == "__main__":
    asyncio.run(main())
