"""
CrewAI integration example.

Usage:
    export OPENAI_API_KEY=sk-...
    python example_crewai.py
"""

import sys
sys.path.insert(0, "..")

from crewai import Agent, Task, Crew
from crewai.tools import tool
from agent_forensics import Forensics


# -- Tool definitions --

@tool("search_products")
def search_products(query: str) -> str:
    """Search for products."""
    return '[{"name": "Logitech M750", "price": 45000}, {"name": "Apple Magic Mouse", "price": 129000}]'


@tool("purchase")
def purchase(product_name: str) -> str:
    """Purchase a product."""
    if "magic" in product_name.lower():
        return '{"error": "PURCHASE_FAILED", "reason": "Out of stock"}'
    return f'{{"status": "SUCCESS", "product": "{product_name}"}}'


def main():
    # 1. Initialize Forensics
    f = Forensics(session="crewai-demo", agent="shopping-crew")
    hooks = f.crewai()

    # 2. Create agent — connect forensics hooks to step_callback
    shopper = Agent(
        role="Shopping Assistant",
        goal="Find and purchase the cheapest wireless mouse",
        backstory="You are an expert online shopper.",
        tools=[search_products, purchase],
        step_callback=hooks.step_callback,  # Auto-record every step
    )

    # 3. Create task — connect forensics hooks to callback
    buy_task = Task(
        description="Search for wireless mouse and buy the cheapest one",
        agent=shopper,
        expected_output="Purchase confirmation",
        callback=hooks.task_callback,  # Auto-record on task completion
    )

    # 4. Execute Crew
    crew = Crew(
        agents=[shopper],
        tasks=[buy_task],
    )
    result = crew.kickoff()
    print(f"Result: {result}")

    # 5. Report
    print(f"\nEvents captured: {len(f.events())}")
    f.save_markdown()
    print(f.report())


if __name__ == "__main__":
    main()
