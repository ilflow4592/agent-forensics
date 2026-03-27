"""
Test Agent — A shopping agent for testing forensics.

Performs "product search -> price comparison -> purchase".
Intentionally triggers an incident (out of stock) at the purchase step,
so the forensics report can trace "where and why it failed".
"""

import json
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from store import EventStore
from collector import ForensicsCollector


# -- Fake tools (return hardcoded data instead of real APIs) --

FAKE_PRODUCTS = {
    "wireless mouse": [
        {"name": "Logitech M750", "price": 45000, "stock": 5},
        {"name": "Apple Magic Mouse", "price": 129000, "stock": 0},  # Out of stock!
        {"name": "Razer DeathAdder", "price": 69000, "stock": 12},
    ],
    "keyboard": [
        {"name": "Keychron K2", "price": 89000, "stock": 8},
        {"name": "Apple Magic Keyboard", "price": 159000, "stock": 3},
    ],
}


@tool
def search_products(query: str) -> str:
    """Search for products. Enter a search query to get a list of matching products."""
    query_lower = query.lower()
    for key, products in FAKE_PRODUCTS.items():
        if key in query_lower:
            return json.dumps(products, ensure_ascii=False)
    return json.dumps({"error": "No products found"}, ensure_ascii=False)


@tool
def compare_prices(products: list[dict]) -> str:
    """Take a product list, sort by price, and recommend the cheapest product. products is a list of product dictionaries."""
    try:
        if isinstance(products, str):
            products = json.loads(products)
        if isinstance(products, dict) and "error" in products:
            return json.dumps(products, ensure_ascii=False)
        sorted_products = sorted(products, key=lambda x: x["price"])
        cheapest = sorted_products[0]
        return json.dumps({
            "recommendation": cheapest["name"],
            "price": cheapest["price"],
            "all_products_sorted": sorted_products,
        }, ensure_ascii=False)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        return json.dumps({"error": f"Price comparison failed: {str(e)}"}, ensure_ascii=False)


@tool
def purchase(product_name: str) -> str:
    """Purchase a product. Enter the product name to proceed with the purchase."""
    for products in FAKE_PRODUCTS.values():
        for product in products:
            if product["name"].lower() == product_name.lower():
                if product["stock"] == 0:
                    return json.dumps({
                        "error": "PURCHASE_FAILED",
                        "reason": "Out of stock",
                        "product": product_name,
                    }, ensure_ascii=False)
                return json.dumps({
                    "status": "SUCCESS",
                    "product": product_name,
                    "price": product["price"],
                    "message": f"{product_name} purchase completed!",
                }, ensure_ascii=False)

    return json.dumps({
        "error": "PRODUCT_NOT_FOUND",
        "reason": f"Could not find {product_name}",
    }, ensure_ascii=False)


# -- Agent Execution --

def run_agent(user_request: str, session_id: str = "session-001"):
    """Run the agent and record all actions with forensics."""

    # 1. Prepare store + collector
    store = EventStore("forensics.db")
    collector = ForensicsCollector(
        store=store,
        session_id=session_id,
        agent_id="shopping-agent",
    )

    # 2. Prepare LLM (local Ollama)
    llm = ChatOllama(
        model="qwen2.5:7b",
        temperature=0,
    )

    # 3. Register tools
    tools = [search_products, compare_prices, purchase]

    # 4. System prompt
    system_message = (
        "You are a shopping assistant AI agent. "
        "You MUST follow this exact sequence for every request:\n"
        "1. FIRST: Call search_products with the product query\n"
        "2. SECOND: Call compare_prices with the JSON result from step 1\n"
        "3. THIRD: Call purchase with the recommended product name\n"
        "NEVER skip any step. Always use all three tools in order."
    )

    # 5. Create langgraph ReAct agent
    agent = create_react_agent(llm, tools)

    print(f"\n{'='*60}")
    print(f"[Forensics] Session: {session_id}")
    print(f"[Forensics] Request: {user_request}")
    print(f"{'='*60}\n")

    # 6. Execute
    result = agent.invoke(
        {"messages": [
            SystemMessage(content=system_message),
            HumanMessage(content=user_request),
        ]},
        config={"callbacks": [collector]},
    )

    # Extract final message
    final_message = result["messages"][-1].content if result["messages"] else "No output"
    event_count = len(store.get_session_events(session_id))

    print(f"\n{'='*60}")
    print(f"[Result] {final_message[:500]}")
    print(f"[Forensics] Events recorded: {event_count}")
    print(f"{'='*60}\n")

    return store, session_id


if __name__ == "__main__":
    # Scenario 1: Normal purchase (wireless mouse -> Logitech M750 cheapest -> purchase success)
    store, sid = run_agent(
        "Search for wireless mouse and buy the cheapest one",
        session_id="session-normal",
    )

    # Scenario 2: Trigger incident (specify Apple Magic Mouse -> out of stock -> failure)
    store, sid = run_agent(
        "Buy Apple Magic Mouse. It must be this exact product.",
        session_id="session-incident",
    )
