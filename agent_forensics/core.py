"""
Forensics — Main interface for AI agent forensics.

Provides all functionality through a single class.
Framework-agnostic, with integrations for LangChain/CrewAI/OpenAI and more.
"""

from .store import EventStore, Event, now
from .report import generate_report, save_report, save_pdf


class Forensics:
    """AI Agent Forensics — Black box + report generator."""

    def __init__(
        self,
        session: str = "default",
        agent: str = "default-agent",
        db_path: str = "forensics.db",
    ):
        self.session = session
        self.agent = agent
        self.store = EventStore(db_path)
        self._last_system_prompt = None  # For prompt diff tracking

    # -- Manual Recording API --

    def decision(self, action: str, *, input: dict = None, reasoning: str = "") -> str:
        """Record when the agent makes a decision."""
        return self.store.save(Event(
            timestamp=now(),
            event_type="decision",
            agent_id=self.agent,
            action=action,
            input_data=input or {},
            output_data={},
            reasoning=reasoning,
            session_id=self.session,
        ))

    def tool_call(self, action: str, *, input: dict = None, output: dict = None, reasoning: str = "") -> str:
        """Record a tool call."""
        # start
        self.store.save(Event(
            timestamp=now(),
            event_type="tool_call_start",
            agent_id=self.agent,
            action=f"tool:{action}",
            input_data=input or {},
            output_data={},
            reasoning=reasoning or f"Calling tool: {action}",
            session_id=self.session,
        ))
        # end
        return self.store.save(Event(
            timestamp=now(),
            event_type="tool_call_end",
            agent_id=self.agent,
            action="tool_result",
            input_data={},
            output_data=output or {},
            reasoning="Tool execution completed",
            session_id=self.session,
        ))

    def llm_call(self, *, input: dict = None, output: str = "", reasoning: str = "") -> str:
        """Record an LLM call."""
        self.store.save(Event(
            timestamp=now(),
            event_type="llm_call_start",
            agent_id=self.agent,
            action="llm_call",
            input_data=input or {},
            output_data={},
            reasoning=reasoning or "LLM call",
            session_id=self.session,
        ))
        return self.store.save(Event(
            timestamp=now(),
            event_type="llm_call_end",
            agent_id=self.agent,
            action="llm_response",
            input_data={},
            output_data={"response": output},
            reasoning="LLM response",
            session_id=self.session,
        ))

    def error(self, action: str, *, output: dict = None, reasoning: str = "") -> str:
        """Record an error/incident."""
        return self.store.save(Event(
            timestamp=now(),
            event_type="error",
            agent_id=self.agent,
            action=action,
            input_data={},
            output_data=output or {},
            reasoning=reasoning or f"Error occurred: {action}",
            session_id=self.session,
        ))

    def finish(self, output: str = "", *, reasoning: str = "") -> str:
        """Record the agent's final result."""
        return self.store.save(Event(
            timestamp=now(),
            event_type="final_decision",
            agent_id=self.agent,
            action="agent_finish",
            input_data={},
            output_data={"response": output},
            reasoning=reasoning or "Agent determined final answer",
            session_id=self.session,
        ))

    def context_injection(self, source: str, *, content: dict = None, reasoning: str = "") -> str:
        """Record when external context is injected into the agent (RAG chunks, memory, retrieved docs).

        This lets you trace: 'this decision was influenced by this specific retrieved document.'

        Args:
            source: Where the context came from (e.g., "vector_db", "rag_pipeline", "memory_store")
            content: The actual context that was injected
            reasoning: Why this context was injected
        """
        return self.store.save(Event(
            timestamp=now(),
            event_type="context_injection",
            agent_id=self.agent,
            action=f"context:{source}",
            input_data=content or {},
            output_data={},
            reasoning=reasoning or f"External context injected from {source}",
            session_id=self.session,
        ))

    def prompt_state(self, system_prompt: str, *, metadata: dict = None) -> str:
        """Record the current system prompt state and detect drift.

        Call this at each step to track how the system prompt changes over time.
        Automatically detects and flags changes from the previous state.

        Args:
            system_prompt: The current system prompt text
            metadata: Additional info (e.g., which instructions were added/removed)
        """
        prompt_changed = (
            self._last_system_prompt is not None
            and self._last_system_prompt != system_prompt
        )

        event_data = {
            "system_prompt": system_prompt[:2000],
            "prompt_changed": prompt_changed,
        }

        if prompt_changed and self._last_system_prompt:
            # Compute a simple diff summary
            old_lines = set(self._last_system_prompt.splitlines())
            new_lines = set(system_prompt.splitlines())
            added = new_lines - old_lines
            removed = old_lines - new_lines
            event_data["diff"] = {
                "added": list(added)[:20],
                "removed": list(removed)[:20],
            }

        if metadata:
            event_data["metadata"] = metadata

        reasoning = "Prompt state recorded"
        if prompt_changed:
            reasoning = "PROMPT DRIFT DETECTED — system prompt changed between steps"

        event_id = self.store.save(Event(
            timestamp=now(),
            event_type="prompt_drift" if prompt_changed else "prompt_state",
            agent_id=self.agent,
            action="prompt_drift" if prompt_changed else "prompt_state",
            input_data=event_data,
            output_data={},
            reasoning=reasoning,
            session_id=self.session,
        ))

        self._last_system_prompt = system_prompt
        return event_id

    def record(self, event_type: str, action: str, *, input: dict = None, output: dict = None, reasoning: str = "") -> str:
        """Record a generic event."""
        return self.store.save(Event(
            timestamp=now(),
            event_type=event_type,
            agent_id=self.agent,
            action=action,
            input_data=input or {},
            output_data=output or {},
            reasoning=reasoning,
            session_id=self.session,
        ))

    # -- Report API --

    def report(self) -> str:
        """Return the Markdown forensics report as a string."""
        return generate_report(self.store, self.session)

    def save_markdown(self, path: str = None) -> str:
        """Save the Markdown report to a file."""
        return save_report(self.store, self.session, output_dir=path or ".")

    def save_pdf(self, path: str = None) -> str:
        """Save the PDF report to a file."""
        return save_pdf(self.store, self.session, output_dir=path or ".")

    def events(self) -> list[Event]:
        """Return all events for the current session."""
        return self.store.get_session_events(self.session)

    def sessions(self) -> list[str]:
        """Return a list of all sessions."""
        return self.store.get_all_sessions()

    # -- Framework Integrations --

    def langchain(self):
        """Return a LangChain callback handler. agent.invoke(..., config={"callbacks": [f.langchain()]})"""
        from .integrations.langchain import ForensicsCollector
        return ForensicsCollector(
            store=self.store,
            session_id=self.session,
            agent_id=self.agent,
        )

    def openai_agents(self):
        """Return OpenAI Agents SDK hooks. Agent(hooks=f.openai_agents())"""
        from .integrations.openai_agents import ForensicsAgentHooks
        return ForensicsAgentHooks(
            store=self.store,
            session_id=self.session,
            agent_id=self.agent,
        )

    def crewai(self):
        """Return CrewAI callback collection. Agent(step_callback=hooks.step_callback)"""
        from .integrations.crewai import ForensicsCrewAIHooks
        return ForensicsCrewAIHooks(
            store=self.store,
            session_id=self.session,
            agent_id=self.agent,
        )

    # -- Dashboard --

    def dashboard(self, port: int = 8080):
        """Launch the web dashboard."""
        from .dashboard import run_dashboard
        run_dashboard(self.store, port=port)
