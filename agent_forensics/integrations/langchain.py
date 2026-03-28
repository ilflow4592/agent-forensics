"""
Forensics Collector — Automatically captures all LangChain agent actions like CCTV.

Implements a LangChain/LangGraph callback handler that
automatically records events to the EventStore whenever
the agent calls an LLM or uses a tool.

Usage:
    collector = ForensicsCollector(store, session_id="session-001")
    agent.invoke({"input": "..."}, config={"callbacks": [collector]})
    -> All agent actions are automatically recorded
"""

from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage

from ..store import EventStore, Event, now


class ForensicsCollector(BaseCallbackHandler):
    """LangChain callback handler — records all agent actions to EventStore."""

    def __init__(self, store: EventStore, session_id: str, agent_id: str = "default-agent"):
        self.store = store
        self.session_id = session_id
        self.agent_id = agent_id
        self._last_system_prompt = None  # For prompt drift tracking

    # -- LLM Call Capture --

    def on_chat_model_start(self, serialized: dict, messages: list, **kwargs) -> None:
        """ChatModel call started. LangGraph ReAct uses chat models."""
        # messages is a list of list of BaseMessage
        flat_messages = []
        system_prompt = None

        for msg_list in messages:
            for msg in msg_list:
                role = msg.__class__.__name__
                content = msg.content[:300] if isinstance(msg.content, str) else str(msg.content)[:300]
                flat_messages.append({"role": role, "content": content})

                # Extract system prompt for drift detection
                if role in ("SystemMessage", "System"):
                    system_prompt = msg.content if isinstance(msg.content, str) else str(msg.content)

        # Detect prompt drift
        if system_prompt is not None:
            prompt_changed = (
                self._last_system_prompt is not None
                and self._last_system_prompt != system_prompt
            )
            if prompt_changed:
                old_lines = set(self._last_system_prompt.splitlines())
                new_lines = set(system_prompt.splitlines())
                self.store.save(Event(
                    timestamp=now(),
                    event_type="prompt_drift",
                    agent_id=self.agent_id,
                    action="prompt_drift",
                    input_data={
                        "system_prompt": system_prompt[:2000],
                        "prompt_changed": True,
                        "diff": {
                            "added": list(new_lines - old_lines)[:20],
                            "removed": list(old_lines - new_lines)[:20],
                        },
                    },
                    output_data={},
                    reasoning="PROMPT DRIFT DETECTED — system prompt changed between steps",
                    session_id=self.session_id,
                ))
            self._last_system_prompt = system_prompt

        self.store.save(Event(
            timestamp=now(),
            event_type="llm_call_start",
            agent_id=self.agent_id,
            action="llm_call",
            input_data={"messages": flat_messages[-3:]},
            output_data={},
            reasoning="Requesting inference from LLM",
            session_id=self.session_id,
        ))

    def on_llm_end(self, response, **kwargs) -> None:
        """LLM response received. Captures both text response and tool_calls."""
        generations = response.generations
        output_text = ""
        tool_calls = []

        if generations and generations[0]:
            gen = generations[0][0]
            output_text = gen.text[:1000] if gen.text else ""

            # LangGraph ReAct: when LLM decides to call a tool, message contains tool_calls
            if hasattr(gen, "message") and isinstance(gen.message, AIMessage):
                ai_msg = gen.message
                if ai_msg.tool_calls:
                    for tc in ai_msg.tool_calls:
                        tool_calls.append({
                            "tool": tc.get("name", "unknown"),
                            "args": str(tc.get("args", {}))[:300],
                            "id": tc.get("id", ""),
                        })

        # tool_calls present -> agent decided "what to do next" (decision event)
        if tool_calls:
            for tc in tool_calls:
                self.store.save(Event(
                    timestamp=now(),
                    event_type="decision",
                    agent_id=self.agent_id,
                    action=f"agent_decision:{tc['tool']}",
                    input_data={"tool_args": tc["args"]},
                    output_data={},
                    reasoning=f"LLM decided to use tool {tc['tool']}. Input: {tc['args']}",
                    session_id=self.session_id,
                ))
        else:
            # No tool_calls -> final answer (final_decision)
            self.store.save(Event(
                timestamp=now(),
                event_type="final_decision" if output_text else "llm_call_end",
                agent_id=self.agent_id,
                action="agent_finish" if output_text else "llm_response",
                input_data={},
                output_data={"response": output_text},
                reasoning="Agent determined final answer" if output_text else "LLM response (empty text)",
                session_id=self.session_id,
            ))

    def on_llm_error(self, error: BaseException, **kwargs) -> None:
        """LLM call failed."""
        self.store.save(Event(
            timestamp=now(),
            event_type="error",
            agent_id=self.agent_id,
            action="llm_error",
            input_data={},
            output_data={"error": str(error)[:500]},
            reasoning=f"LLM call failed: {type(error).__name__}",
            session_id=self.session_id,
        ))

    # -- Tool Call Capture --

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        """Agent started using a tool."""
        tool_name = serialized.get("name", "unknown_tool")
        self.store.save(Event(
            timestamp=now(),
            event_type="tool_call_start",
            agent_id=self.agent_id,
            action=f"tool:{tool_name}",
            input_data={"tool_input": input_str[:500]},
            output_data={},
            reasoning=f"Agent decided to use tool {tool_name}",
            session_id=self.session_id,
        ))

    def on_tool_end(self, output, **kwargs) -> None:
        """Tool execution completed."""
        # output may be a ToolMessage
        result_str = ""
        if hasattr(output, "content"):
            result_str = str(output.content)[:1000]
        else:
            result_str = str(output)[:1000]

        self.store.save(Event(
            timestamp=now(),
            event_type="tool_call_end",
            agent_id=self.agent_id,
            action="tool_result",
            input_data={},
            output_data={"result": result_str},
            reasoning="Tool execution completed, returning result to agent",
            session_id=self.session_id,
        ))

    def on_tool_error(self, error: BaseException, **kwargs) -> None:
        """Tool execution failed."""
        self.store.save(Event(
            timestamp=now(),
            event_type="error",
            agent_id=self.agent_id,
            action="tool_error",
            input_data={},
            output_data={"error": str(error)[:500]},
            reasoning=f"Tool execution failed: {type(error).__name__}",
            session_id=self.session_id,
        ))
