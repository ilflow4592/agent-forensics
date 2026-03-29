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

    def llm_call(self, *, input: dict = None, output: str = "",
                 model: str = None, temperature: float = None, seed: int = None,
                 reasoning: str = "") -> str:
        """Record an LLM call with model config for deterministic replay.

        Args:
            input: What was sent to the LLM
            output: What the LLM returned
            model: Model name (e.g., "gpt-4o", "claude-sonnet-4-20250514")
            temperature: Temperature setting used
            seed: Random seed (if supported by the model)
            reasoning: Why this LLM call was made
        """
        model_config = {}
        if model: model_config["model"] = model
        if temperature is not None: model_config["temperature"] = temperature
        if seed is not None: model_config["seed"] = seed

        input_data = input or {}
        if model_config:
            input_data["_model_config"] = model_config

        self.store.save(Event(
            timestamp=now(),
            event_type="llm_call_start",
            agent_id=self.agent,
            action="llm_call",
            input_data=input_data,
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

    def guardrail(self, *, intent: str, action: str, allowed: bool, reason: str = "") -> str:
        """Record a guardrail checkpoint — was this action allowed or blocked?

        Use this before critical actions (purchases, data access, external API calls)
        to log whether the action passed or was blocked, and why.

        Args:
            intent: What the agent intended to do (e.g., "check price")
            action: What the agent actually did or tried (e.g., "purchase item")
            allowed: Whether the action was permitted
            reason: Why it was allowed or blocked
        """
        event_type = "guardrail_pass" if allowed else "guardrail_block"
        return self.store.save(Event(
            timestamp=now(),
            event_type=event_type,
            agent_id=self.agent,
            action=f"guardrail:{action}",
            input_data={"intent": intent, "action": action, "allowed": allowed},
            output_data={},
            reasoning=reason or (f"Action '{action}' {'allowed' if allowed else 'BLOCKED'} — intent was '{intent}'"),
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

    def classify(self, session_id: str = None) -> list[dict]:
        """Auto-classify failure modes in a session's event trace.

        Returns a list of detected failures, each with:
        - type: failure category (e.g., INSTRUCTION_CONFLICT, MISSING_APPROVAL)
        - severity: HIGH / MEDIUM / LOW
        - description: human-readable explanation
        - evidence: relevant data from the trace
        - step: which step in the timeline
        """
        from .classifier import classify_failures
        events = self.store.get_session_events(session_id or self.session)
        return classify_failures(events)

    def failure_stats(self, session_ids: list[str] = None) -> dict:
        """Aggregate failure patterns across multiple sessions.

        Args:
            session_ids: List of sessions to analyze. If None, analyzes all sessions.

        Returns:
            Dict with total failures, breakdown by type, and severity distribution.
        """
        from .classifier import classify_failures, failure_summary
        sids = session_ids or self.store.get_all_sessions()
        all_failures = []
        for sid in sids:
            events = self.store.get_session_events(sid)
            all_failures.extend(classify_failures(events))
        return failure_summary(all_failures)

    # -- Replay API --

    def get_replay_config(self, session_id: str = None) -> dict:
        """Extract model config and input sequence from a recorded session for replay.

        Returns a dict with:
        - model_config: {model, temperature, seed} from the first LLM call
        - steps: list of {type, action, input, output} for each step
        - tool_responses: dict mapping tool calls to their recorded outputs

        Usage:
            config = f.get_replay_config("session-123")
            print(config["model_config"])   # {'model': 'gpt-4o', 'temperature': 0}
            print(config["steps"])          # [{type, action, input, output}, ...]
        """
        sid = session_id or self.session
        events = self.store.get_session_events(sid)

        model_config = {}
        steps = []
        tool_responses = {}

        for event in events:
            # Extract model config from first LLM call
            if event.event_type == "llm_call_start" and not model_config:
                mc = event.input_data.get("_model_config", {})
                if mc:
                    model_config = mc

            # Build step sequence
            steps.append({
                "type": event.event_type,
                "action": event.action,
                "input": event.input_data,
                "output": event.output_data,
                "reasoning": event.reasoning,
                "timestamp": event.timestamp,
            })

            # Map tool calls to their responses for replay
            if event.event_type == "tool_call_end":
                tool_responses[event.action] = event.output_data

        return {
            "session_id": sid,
            "model_config": model_config,
            "steps": steps,
            "tool_responses": tool_responses,
            "total_events": len(events),
        }

    def replay_diff(self, original_session: str, replay_session: str) -> dict:
        """Compare two sessions (original vs replay) and return differences.

        Usage:
            # 1. Get original config
            config = f.get_replay_config("session-123")

            # 2. Re-run your agent with same config, recording to a new session
            f2 = Forensics(session="session-123-replay")
            # ... run agent with config["model_config"] ...

            # 3. Compare
            diff = f.replay_diff("session-123", "session-123-replay")
            print(diff["matching"])       # True/False
            print(diff["divergences"])    # List of differences
        """
        original = self.store.get_session_events(original_session)
        replayed = self.store.get_session_events(replay_session)

        # Compare decision sequences
        orig_decisions = [
            {"action": e.action, "reasoning": e.reasoning, "output": e.output_data}
            for e in original
            if e.event_type in ("decision", "final_decision", "tool_call_end")
        ]
        replay_decisions = [
            {"action": e.action, "reasoning": e.reasoning, "output": e.output_data}
            for e in replayed
            if e.event_type in ("decision", "final_decision", "tool_call_end")
        ]

        divergences = []
        max_len = max(len(orig_decisions), len(replay_decisions))

        for i in range(max_len):
            orig = orig_decisions[i] if i < len(orig_decisions) else None
            repl = replay_decisions[i] if i < len(replay_decisions) else None

            if orig is None:
                divergences.append({
                    "step": i + 1,
                    "type": "extra_in_replay",
                    "replay": repl,
                })
            elif repl is None:
                divergences.append({
                    "step": i + 1,
                    "type": "missing_in_replay",
                    "original": orig,
                })
            elif orig["action"] != repl["action"] or orig["output"] != repl["output"]:
                divergences.append({
                    "step": i + 1,
                    "type": "diverged",
                    "original": orig,
                    "replay": repl,
                })

        return {
            "original_session": original_session,
            "replay_session": replay_session,
            "original_events": len(original),
            "replay_events": len(replayed),
            "original_decisions": len(orig_decisions),
            "replay_decisions": len(replay_decisions),
            "matching": len(divergences) == 0,
            "divergences": divergences,
        }

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
