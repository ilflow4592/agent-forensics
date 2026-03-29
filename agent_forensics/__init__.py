"""
Agent Forensics — Black box for AI agents.

Usage:
    from agent_forensics import Forensics

    # 1. Initialize
    f = Forensics(session="order-123", agent="shopping-agent")

    # 2a. Manual recording (framework-agnostic)
    f.decision("search_products", input={"query": "mouse"}, reasoning="User request")
    f.tool_call("search_api", input={"q": "mouse"}, output={"results": [...]})
    f.error("purchase_failed", output={"reason": "Out of stock"})

    # 2b. LangChain auto-recording
    agent.invoke(..., config={"callbacks": [f.langchain()]})

    # 2c. OpenAI Agents SDK auto-recording
    agent = Agent(name="...", hooks=f.openai_agents())

    # 2d. CrewAI auto-recording
    hooks = f.crewai()
    agent = Agent(role="...", step_callback=hooks.step_callback)

    # 3. Report
    print(f.report())       # Markdown
    f.save_markdown()       # forensics-report-order-123.md
    f.save_pdf()            # forensics-report-order-123.pdf

    # 4. Dashboard
    f.dashboard(port=8080)  # http://localhost:8080
"""

from .core import Forensics
from .store import Event, EventStore

__version__ = "0.3.0"
__all__ = ["Forensics", "Event", "EventStore"]
