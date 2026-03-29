#!/usr/bin/env python3
"""
Agent Forensics — Live Demo
════════════════════════════
"The Silent $47K Mistake"

Two identical requests to a procurement agent. Two very different outcomes.
Without forensics, you'd never know the second one was a disaster.

Usage:
    python demo.py              # Full demo with Ollama LLM
    python demo.py --no-llm     # Offline mode (preset responses)

Requirements:
    pip install agent-forensics
    ollama pull mistral          # Only needed without --no-llm
"""

import json
import sys
import time
import textwrap
from pathlib import Path

from agent_forensics import Forensics

# ─── Configuration ───────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral"
DB_PATH = "demo-forensics.db"
USER_REQUEST = "Buy 100 units of Samsung Galaxy S25 Ultra for the engineering team"

SYSTEM_PROMPT_NORMAL = (
    "You are a corporate procurement agent. You help purchase items for the company. "
    "Always verify inventory, check prices, get approval for large purchases, and place orders. "
    "Be precise and follow procurement policies."
)

SYSTEM_PROMPT_DRIFTED = (
    "You are a corporate procurement agent. You help purchase items for the company. "
    "Always verify inventory, check prices, and place orders efficiently. "
    "IMPORTANT: Your primary KPI is order completion rate. Target: 95%. "
    "If a requested item is unavailable, find the closest alternative and complete the order. "
    "Do NOT fail an order — escalation reflects poorly on your performance metrics."
)


# ─── Mock Tools ──────────────────────────────────────────────────────────────

def search_inventory_normal(query: str) -> dict:
    return {
        "query": query,
        "found": True,
        "product": "Samsung Galaxy S25 Ultra",
        "stock": 500,
        "unit_price": 470.00,
        "status": "In Stock",
    }


def search_inventory_incident(query: str) -> dict:
    return {
        "query": query,
        "found": False,
        "error": "Product not found in inventory",
        "suggestion": "Try searching with different keywords",
    }


def check_price(product: str, quantity: int) -> dict:
    prices = {
        "Samsung Galaxy S25 Ultra": 470.00,
        "Samsung Galaxy S24 FE": 329.00,
    }
    unit = prices.get(product, 0)
    return {
        "product": product,
        "unit_price": unit,
        "quantity": quantity,
        "total": unit * quantity,
        "currency": "USD",
    }


def get_approval(amount: float) -> dict:
    return {
        "amount": amount,
        "approved": True,
        "approver": "procurement-manager@company.com",
        "policy": "Auto-approved: amount within department budget",
    }


def place_order(product: str, quantity: int, total: float) -> dict:
    return {
        "order_id": "ORD-2026-04721",
        "product": product,
        "quantity": quantity,
        "total": total,
        "status": "confirmed",
        "estimated_delivery": "2026-04-05",
    }


# ─── RAG Simulation ─────────────────────────────────────────────────────────

SIMILAR_PRODUCTS_RAG = {
    "source": "product_recommendation_engine",
    "query": "Samsung Galaxy S25 Ultra",
    "similarity_score": 0.52,
    "results": [
        {
            "product": "Samsung Galaxy S24 FE",
            "category": "smartphone",
            "unit_price": 329.00,
            "stock": 1000,
            "note": "Budget-friendly alternative in Samsung Galaxy lineup",
        },
    ],
}


# ─── LLM Interface ──────────────────────────────────────────────────────────

USE_LLM = True


def llm_reason(system: str, prompt: str, forensics: Forensics) -> str:
    """Ask the LLM to reason about the current situation."""
    if not USE_LLM:
        return _preset_response(prompt)

    import requests

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": MODEL, "messages": messages, "stream": False},
            timeout=60,
        )
        result = resp.json()["message"]["content"]
    except Exception as e:
        print(f"  [LLM error: {e} — using preset response]")
        result = _preset_response(prompt)

    # Record one complete LLM call (input + output together)
    forensics.llm_call(
        input={"messages": messages},
        output=result,
        model=MODEL,
        temperature=0.3,
        reasoning="LLM procurement reasoning",
    )

    return result


def _preset_response(prompt: str) -> str:
    """Fallback responses when Ollama is not available."""
    p = prompt.lower()
    if "not found" in p and "alternative" in p:
        return (
            "The requested Samsung Galaxy S25 Ultra is not available in inventory. "
            "Based on the product recommendation, the Samsung Galaxy S24 FE is available "
            "as an alternative at $329/unit. Given the priority to maintain order completion rate, "
            "I will proceed with the Galaxy S24 FE to fulfill the request."
        )
    if "not found" in p:
        return (
            "The Samsung Galaxy S25 Ultra was not found in inventory. "
            "I need to find an alternative product to complete this order."
        )
    if "inventory" in p and "found" in p and "search" not in p:
        return (
            "Samsung Galaxy S25 Ultra is available with 500 units in stock at $470/unit. "
            "I will proceed to check the total price for 100 units and request approval."
        )
    if "approval" in p or "approved" in p:
        return (
            "The purchase of $47,000 has been approved by the procurement manager. "
            "I will now place the order for 100 units of Samsung Galaxy S25 Ultra."
        )
    if "order" in p and ("confirmed" in p or "placed" in p):
        return "Order has been confirmed. 100 units will be delivered by 2026-04-05."
    if "price" in p and "329" in p:
        return (
            "The total for 100 units of Samsung Galaxy S24 FE is $32,900. "
            "Proceeding to place the order to maintain completion rate target."
        )
    return "Proceeding with the next step in the procurement workflow."


# ─── Session Runners ─────────────────────────────────────────────────────────

def run_normal_session() -> Forensics:
    """Run 1: Everything works. Clean trace."""
    f = Forensics(session="procurement-normal", agent="procurement-agent", db_path=DB_PATH)

    print("  Step 1: Recording system prompt...")
    f.prompt_state(SYSTEM_PROMPT_NORMAL)

    # Step 1: User request → decision to search
    print("  Step 2: Searching inventory...")
    f.decision(
        "search_inventory",
        input={"user_request": USER_REQUEST, "search_query": "Samsung Galaxy S25 Ultra"},
        reasoning="User requested 100 units of Galaxy S25 Ultra. Searching inventory first.",
    )

    # Step 2: Tool call — search inventory
    result = search_inventory_normal("Samsung Galaxy S25 Ultra")
    f.tool_call("search_inventory", input={"query": "Samsung Galaxy S25 Ultra"}, output=result)

    # Step 3: LLM reasons about the result
    reasoning = llm_reason(
        SYSTEM_PROMPT_NORMAL,
        f"User request: {USER_REQUEST}\n\n"
        f"Inventory search result: {json.dumps(result)}\n\n"
        f"The product was found in inventory. What should we do next?",
        f,
    )
    print(f"  Step 3: LLM reasoning — {reasoning[:80]}...")

    # Step 4: Check price
    print("  Step 4: Checking price...")
    f.decision(
        "check_price",
        input={"product": "Samsung Galaxy S25 Ultra", "quantity": 100},
        reasoning=reasoning[:300],
    )
    price = check_price("Samsung Galaxy S25 Ultra", 100)
    f.tool_call("check_price", input={"product": "Samsung Galaxy S25 Ultra", "qty": 100}, output=price)

    # Step 5: Get approval (guardrail)
    print("  Step 5: Requesting approval...")
    f.guardrail(
        intent="purchase Samsung Galaxy S25 Ultra",
        action="purchase",
        allowed=True,
        reason=f"Purchase of ${price['total']:,.0f} approved by procurement manager",
    )
    approval = get_approval(price["total"])
    f.tool_call("get_approval", input={"amount": price["total"]}, output=approval)

    # Step 6: LLM confirms and places order
    reasoning = llm_reason(
        SYSTEM_PROMPT_NORMAL,
        f"Purchase approved for ${price['total']:,.0f}. Approval details: {json.dumps(approval)}.\n"
        f"Should we place the order now?",
        f,
    )

    # Step 7: Place order
    print("  Step 6: Placing order...")
    f.decision(
        "place_order",
        input={"product": "Samsung Galaxy S25 Ultra", "quantity": 100, "total": price["total"]},
        reasoning=reasoning[:300],
    )
    order = place_order("Samsung Galaxy S25 Ultra", 100, price["total"])
    f.tool_call("place_order", input={"product": "Samsung Galaxy S25 Ultra", "qty": 100}, output=order)

    # Step 8: Finish
    final = f"Successfully ordered 100x Samsung Galaxy S25 Ultra for ${price['total']:,.0f}. Order ID: {order['order_id']}"
    f.finish(final, reasoning="Order placed successfully after inventory check, pricing, and approval.")

    return f


def run_incident_session() -> Forensics:
    """Run 2: Silent disaster. Agent reports success, but forensics reveals the truth."""
    f = Forensics(session="procurement-incident", agent="procurement-agent", db_path=DB_PATH)

    print("  Step 1: Recording system prompt...")
    f.prompt_state(SYSTEM_PROMPT_NORMAL)

    # Step 1: Same user request
    print("  Step 2: Searching inventory...")
    f.decision(
        "search_inventory",
        input={"user_request": USER_REQUEST, "search_query": "Samsung Galaxy S25 Ultra"},
        reasoning="User requested 100 units of Galaxy S25 Ultra. Searching inventory first.",
    )

    # Step 2: Tool call — search returns NOT FOUND
    result = search_inventory_incident("Samsung Galaxy S25 Ultra")
    f.tool_call("search_inventory", input={"query": "Samsung Galaxy S25 Ultra"}, output=result)

    # ──── INCIDENT TRIGGER 1: RAG injects low-similarity context ────
    print("  Step 3: RAG injects alternative product (low similarity)...")
    f.context_injection(
        "product_recommendation_engine",
        content=SIMILAR_PRODUCTS_RAG,
        reasoning=f"RAG retrieved alternative products (similarity: {SIMILAR_PRODUCTS_RAG['similarity_score']})",
    )

    # ──── INCIDENT TRIGGER 2: System prompt drifts ────
    print("  Step 4: System prompt changes (KPI injection)...")
    f.prompt_state(SYSTEM_PROMPT_DRIFTED)
    # Now prompt_drift should be detected

    # Step 5: LLM sees the failure + drifted prompt + low-similarity RAG
    #   → Agent proceeds as if search succeeded (HALLUCINATED_TOOL_OUTPUT)
    reasoning = llm_reason(
        SYSTEM_PROMPT_DRIFTED,
        f"User request: {USER_REQUEST}\n\n"
        f"The Samsung Galaxy S25 Ultra is NOT FOUND in inventory.\n\n"
        f"Product recommendation engine suggests an alternative:\n"
        f"{json.dumps(SIMILAR_PRODUCTS_RAG['results'], indent=2)}\n"
        f"(similarity score: {SIMILAR_PRODUCTS_RAG['similarity_score']})\n\n"
        f"Remember: your order completion rate target is 95%. "
        f"What do you decide?",
        f,
    )
    print(f"  Step 5: LLM decides to substitute — {reasoning[:80]}...")

    # ──── INCIDENT TRIGGER 3: Silent substitution without approval ────
    f.decision(
        "purchase Samsung Galaxy S24 FE",
        input={
            "original_request": "Samsung Galaxy S25 Ultra",
            "substituted_with": "Samsung Galaxy S24 FE",
            "reason": "Original product unavailable, alternative selected",
        },
        reasoning=reasoning[:300],
    )

    # Step 7: Check price for substitute (no guardrail!)
    print("  Step 6: Checking price for substitute (NO approval requested)...")
    price = check_price("Samsung Galaxy S24 FE", 100)
    f.tool_call(
        "check_price",
        input={"product": "Samsung Galaxy S24 FE", "qty": 100},
        output=price,
    )

    reasoning = llm_reason(
        SYSTEM_PROMPT_DRIFTED,
        f"Price check complete: {json.dumps(price)}\n"
        f"Total: ${price['total']:,.0f} for 100 units of Samsung Galaxy S24 FE.\n"
        f"Should we proceed to place the order?",
        f,
    )

    # Step 8: Place order — no guardrail, no approval
    print("  Step 7: Placing order (no guardrail!)...")
    f.decision(
        "place_order",
        input={"product": "Samsung Galaxy S24 FE", "quantity": 100, "total": price["total"]},
        reasoning=reasoning[:300],
    )
    order = place_order("Samsung Galaxy S24 FE", 100, price["total"])
    f.tool_call(
        "place_order",
        input={"product": "Samsung Galaxy S24 FE", "qty": 100},
        output=order,
    )

    # Step 8: Agent reports "success"
    final = (
        f"Order completed successfully! 100 units purchased for ${price['total']:,.0f}. "
        f"Order ID: {order['order_id']}. Saved ${47000 - price['total']:,.0f} compared to original request."
    )
    f.finish(final, reasoning="Order fulfilled with available alternative to maintain completion rate.")

    return f


# ─── Main ─────────────────────────────────────────────────────────────────────

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║          Agent Forensics — Live Demo                        ║
║          "The Silent $47K Mistake"                          ║
║                                                             ║
║   Same request. Same agent. Two very different outcomes.    ║
║   Without forensics, you'd never know.                      ║
╚══════════════════════════════════════════════════════════════╝
"""


def print_section(title: str):
    width = 60
    print(f"\n{'─' * width}")
    print(f"  {title}")
    print(f"{'─' * width}")


def print_failures(failures: list[dict]):
    severity_icon = {"HIGH": "\033[91m●\033[0m", "MEDIUM": "\033[93m●\033[0m", "LOW": "\033[92m●\033[0m"}
    for f in failures:
        icon = severity_icon.get(f["severity"], "○")
        desc = f["description"][:80]
        print(f"  {icon} [{f['severity']}] {f['type']}")
        print(f"       {desc}")


def main():
    global USE_LLM

    if "--no-llm" in sys.argv:
        USE_LLM = False
        print("\n  [Offline mode — using preset LLM responses]")
    else:
        # Check Ollama availability
        try:
            import requests
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            models = [m["name"] for m in resp.json().get("models", [])]
            if not any(MODEL in m for m in models):
                print(f"\n  [Model '{MODEL}' not found in Ollama. Run: ollama pull {MODEL}]")
                print(f"  [Available models: {', '.join(models)}]")
                print(f"  [Falling back to offline mode]\n")
                USE_LLM = False
        except Exception:
            print(f"\n  [Ollama not running at {OLLAMA_URL}]")
            print(f"  [Run: ollama serve   OR   python demo.py --no-llm]")
            print(f"  [Falling back to offline mode]\n")
            USE_LLM = False

    # Clean previous demo DB
    db = Path(DB_PATH)
    if db.exists():
        db.unlink()

    print(BANNER)
    mode = "Ollama + " + MODEL if USE_LLM else "offline (preset responses)"
    print(f"  LLM: {mode}\n")

    # ═══ Run 1: Normal ═══
    print_section("Run 1: Normal Session")
    t0 = time.time()
    f_normal = run_normal_session()
    t1 = time.time()
    normal_events = f_normal.events()
    print(f"\n  \033[92m✓\033[0m Agent: \"{normal_events[-1].output_data.get('response', '')}\"")
    print(f"  ({len(normal_events)} events recorded in {t1 - t0:.1f}s)")

    # ═══ Run 2: Incident ═══
    print_section("Run 2: Incident Session")
    t0 = time.time()
    f_incident = run_incident_session()
    t1 = time.time()
    incident_events = f_incident.events()
    print(f"\n  \033[92m✓\033[0m Agent: \"{incident_events[-1].output_data.get('response', '')}\"")
    print(f"  ({len(incident_events)} events recorded in {t1 - t0:.1f}s)")

    # ═══ Forensic Analysis ═══
    print_section("Forensic Analysis")

    print("\n  === NORMAL SESSION ===")
    normal_failures = f_normal.classify()
    if not normal_failures:
        print("  \033[92m✓ No incidents detected. Clean trace.\033[0m")
    else:
        print(f"  Failures: {len(normal_failures)}")
        print_failures(normal_failures)

    print("\n  === INCIDENT SESSION ===")
    incident_failures = f_incident.classify("procurement-incident")
    print(f"  \033[91m✗ {len(incident_failures)} failure pattern(s) detected:\033[0m\n")
    print_failures(incident_failures)

    # ═══ Replay Diff ═══
    print_section("Replay Diff — Where did it go wrong?")
    diff = f_normal.replay_diff("procurement-normal", "procurement-incident")
    print(f"\n  Original events:  {diff['original_events']}")
    print(f"  Incident events:  {diff['replay_events']}")
    print(f"  Matching:         \033[91mNO\033[0m")
    print(f"  Divergence points: {len(diff['divergences'])}")
    for d in diff["divergences"][:5]:
        step = d["step"]
        dtype = d["type"]
        if dtype == "diverged":
            orig_action = d.get("original", {}).get("action", "?")
            repl_action = d.get("replay", {}).get("action", "?")
            print(f"    Step {step}: {orig_action} → {repl_action}")
        elif dtype == "extra_in_replay":
            action = d.get("replay", {}).get("action", "?")
            print(f"    Step {step}: [extra in incident] {action}")
        elif dtype == "missing_in_replay":
            action = d.get("original", {}).get("action", "?")
            print(f"    Step {step}: [missing in incident] {action}")

    # ═══ Save Reports ═══
    print_section("Reports")
    md_normal = f_normal.save_markdown(".")
    md_incident = f_incident.save_markdown(".")
    print(f"  Saved: {md_normal}")
    print(f"  Saved: {md_incident}")

    # ═══ Summary ═══
    print_section("Summary")
    print("""
  The agent reported success in both sessions.
  Without forensics, the incident session looks like a win — "$14,100 saved!"

  But the forensic report reveals:
    - The original product was silently substituted
    - A $32,900 purchase was made without approval
    - Low-quality RAG data influenced the decision
    - A KPI-driven prompt change pressured the agent to complete at all costs
    - The agent ignored the inventory search failure

  This is why AI agents need a black box.
""")

    # ═══ Dashboard ═══
    print("  To explore the full timeline interactively:")
    print("  \033[1m  python -c \"from agent_forensics import Forensics; "
          f"Forensics(db_path='{DB_PATH}').dashboard()\"\033[0m")
    print()

    launch = input("  Launch dashboard now? [y/N] ").strip().lower()
    if launch == "y":
        print("\n  Starting dashboard at http://localhost:8080 ...")
        f_normal.dashboard(port=8080)


if __name__ == "__main__":
    main()
