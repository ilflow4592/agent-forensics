"""
CrewAI integration — Captures all actions via step_callback and task_callback.

Usage:
    from agent_forensics import Forensics
    from crewai import Agent, Task, Crew

    f = Forensics(session="order-123")
    hooks = f.crewai()

    agent = Agent(
        role="shopper",
        goal="...",
        step_callback=hooks.step_callback,  # Capture every step
    )

    task = Task(
        description="...",
        agent=agent,
        callback=hooks.task_callback,       # Capture on task completion
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        step_callback=hooks.step_callback,  # Also available at Crew level
    )
"""

from ..store import EventStore, Event, now


class ForensicsCrewAIHooks:
    """Forensics callback collection for CrewAI."""

    def __init__(self, store: EventStore, session_id: str, agent_id: str = "crewai-agent"):
        self.store = store
        self.session_id = session_id
        self.agent_id = agent_id

    def step_callback(self, step_output) -> None:
        """
        Called on every agent step.
        step_output is an AgentAction, ToolResult, or other intermediate result.
        """
        output_str = str(step_output)[:1000]

        # AgentAction case (tool call decision)
        if hasattr(step_output, "tool") and hasattr(step_output, "tool_input"):
            self.store.save(Event(
                timestamp=now(),
                event_type="decision",
                agent_id=self.agent_id,
                action=f"agent_decision:{step_output.tool}",
                input_data={"tool_input": str(step_output.tool_input)[:500]},
                output_data={},
                reasoning=getattr(step_output, "log", "")[:500] or f"Agent decided to use tool {step_output.tool}",
                session_id=self.session_id,
            ))
            return

        # ToolResult case
        if hasattr(step_output, "result"):
            result = str(step_output.result)[:1000]
            is_error = "error" in result.lower() or "fail" in result.lower()
            self.store.save(Event(
                timestamp=now(),
                event_type="error" if is_error else "tool_call_end",
                agent_id=self.agent_id,
                action="tool_result",
                input_data={},
                output_data={"result": result},
                reasoning="Tool execution failed" if is_error else "Tool execution completed",
                session_id=self.session_id,
            ))
            return

        # Other (LLM response, etc.)
        self.store.save(Event(
            timestamp=now(),
            event_type="llm_call_end",
            agent_id=self.agent_id,
            action="step_output",
            input_data={},
            output_data={"output": output_str},
            reasoning="Agent step completed",
            session_id=self.session_id,
        ))

    def task_callback(self, task_output) -> None:
        """
        Called on task completion.
        task_output is a TaskOutput object.
        """
        description = getattr(task_output, "description", "unknown task")
        raw = getattr(task_output, "raw", str(task_output))
        key = getattr(task_output, "key", "")

        self.store.save(Event(
            timestamp=now(),
            event_type="final_decision",
            agent_id=self.agent_id,
            action=f"task_complete:{key}" if key else "task_complete",
            input_data={"task_description": str(description)[:500]},
            output_data={"result": str(raw)[:1000]},
            reasoning=f"Task completed: {str(description)[:200]}",
            session_id=self.session_id,
        ))
