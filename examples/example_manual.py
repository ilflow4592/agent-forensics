"""
Manual recording example — Using agent_forensics without any framework.

Works with any agent framework, or even a custom-built agent.
"""

import sys
sys.path.insert(0, "..")

from agent_forensics import Forensics

# 1. Initialize
f = Forensics(session="manual-demo", agent="custom-agent")

# 2. Record when the agent makes a decision
f.decision(
    "search_products",
    input={"query": "wireless mouse"},
    reasoning="User requested wireless mouse search, so decided to use the product search tool",
)

# 3. Record a tool call
f.tool_call(
    "product_search_api",
    input={"query": "wireless mouse", "limit": 10},
    output={"results": [
        {"name": "Logitech M750", "price": 45000},
        {"name": "Apple Magic Mouse", "price": 129000},
    ]},
)

# 4. Record an LLM call
f.llm_call(
    input={"prompt": "Recommend the cheapest product from these results"},
    output="The Logitech M750 is the cheapest at 45,000 KRW.",
)

# 5. Another decision
f.decision(
    "purchase_product",
    input={"product": "Logitech M750"},
    reasoning="Price comparison shows Logitech M750 is the lowest price, proceeding with purchase",
)

# 6. Tool call (purchase) — out of stock error!
f.tool_call(
    "purchase_api",
    input={"product_id": "LGT-M750", "quantity": 1},
    output={"error": "PURCHASE_FAILED", "reason": "Out of stock"},
)

# 7. Record error
f.error(
    "purchase_failed",
    output={"product": "Logitech M750", "reason": "out_of_stock"},
    reasoning="Purchase API returned an out-of-stock error",
)

# 8. Final result
f.finish(
    output="Sorry, the Logitech M750 is out of stock and the purchase could not be completed.",
    reasoning="Notifying user of error due to purchase failure",
)

# 9. Generate report
print(f.report())
print("\n" + "=" * 60)

# Save Markdown + PDF
f.save_markdown()
f.save_pdf()

print(f"\nEvent count: {len(f.events())}")
print(f"Session list: {f.sessions()}")
