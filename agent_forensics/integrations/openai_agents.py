"""
OpenAI Agents SDK integration — Implements AgentHooks to automatically capture all actions.

Usage:
    from agent_forensics import Forensics
    from agents import Agent, Runner

    f = Forensics(session="order-123")

    agent = Agent(
        name="shopping-agent",
        instructions="...",
        tools=[...],
        hooks=f.openai_agents(),  # Just this one line
    )

    result = await Runner.run(agent, "Buy me a wireless mouse")
"""

from agents.lifecycle import AgentHooks
from agents.run_context import RunContextWrapper, AgentHookContext

from ..store import EventStore, Event, now


class ForensicsAgentHooks(AgentHooks):
    """Forensics hooks for the OpenAI Agents SDK."""

    def __init__(self, store: EventStore, session_id: str, agent_id: str = "default-agent"):
        self.store = store
        self.session_id = session_id
        self.agent_id = agent_id

    async def on_start(self, context: AgentHookContext, agent) -> None:
        """Agent execution started."""
        self.agent_id = agent.name or self.agent_id
        self.store.save(Event(
            timestamp=now(),
            event_type="decision",
            agent_id=self.agent_id,
            action="agent_start",
            input_data={"agent_name": agent.name},
            output_data={},
            reasoning=f"Agent '{agent.name}' execution started",
            session_id=self.session_id,
        ))

    async def on_end(self, context: AgentHookContext, agent, output) -> None:
        """Agent execution finished."""
        output_str = str(output)[:1000] if output else ""
        self.store.save(Event(
            timestamp=now(),
            event_type="final_decision",
            agent_id=self.agent_id,
            action="agent_finish",
            input_data={},
            output_data={"response": output_str},
            reasoning="Agent determined final answer",
            session_id=self.session_id,
        ))

    async def on_llm_start(self, context: RunContextWrapper, agent, system_prompt, input_items) -> None:
        """LLM call started."""
        # Extract last message from input_items
        last_input = ""
        if input_items:
            last_item = input_items[-1]
            if isinstance(last_item, dict):
                last_input = str(last_item.get("content", ""))[:300]
            else:
                last_input = str(last_item)[:300]

        self.store.save(Event(
            timestamp=now(),
            event_type="llm_call_start",
            agent_id=self.agent_id,
            action="llm_call",
            input_data={
                "system_prompt": (system_prompt or "")[:300],
                "last_input": last_input,
            },
            output_data={},
            reasoning="Requesting inference from LLM",
            session_id=self.session_id,
        ))

    async def on_llm_end(self, context: RunContextWrapper, agent, response) -> None:
        """LLM response received."""
        # Extract tool_calls and text from response
        output_text = ""
        tool_calls = []

        if hasattr(response, "output"):
            for item in response.output:
                if hasattr(item, "content"):
                    # Text response
                    if isinstance(item.content, list):
                        for c in item.content:
                            if hasattr(c, "text"):
                                output_text += c.text
                    elif isinstance(item.content, str):
                        output_text += item.content
                elif hasattr(item, "name"):
                    # tool call
                    tool_calls.append({
                        "tool": getattr(item, "name", "unknown"),
                        "args": str(getattr(item, "arguments", ""))[:300],
                        "call_id": getattr(item, "call_id", ""),
                    })

        # tool_calls -> decision event
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

        # Text response
        if output_text:
            self.store.save(Event(
                timestamp=now(),
                event_type="llm_call_end",
                agent_id=self.agent_id,
                action="llm_response",
                input_data={},
                output_data={"response": output_text[:1000]},
                reasoning="LLM returned a response",
                session_id=self.session_id,
            ))

    async def on_tool_start(self, context: RunContextWrapper, agent, tool) -> None:
        """Tool call started."""
        tool_name = getattr(tool, "name", str(type(tool).__name__))
        self.store.save(Event(
            timestamp=now(),
            event_type="tool_call_start",
            agent_id=self.agent_id,
            action=f"tool:{tool_name}",
            input_data={"tool_name": tool_name},
            output_data={},
            reasoning=f"Agent decided to use tool {tool_name}",
            session_id=self.session_id,
        ))

    async def on_tool_end(self, context: RunContextWrapper, agent, tool, result: str) -> None:
        """Tool execution completed."""
        tool_name = getattr(tool, "name", str(type(tool).__name__))
        self.store.save(Event(
            timestamp=now(),
            event_type="tool_call_end",
            agent_id=self.agent_id,
            action=f"tool_result:{tool_name}",
            input_data={},
            output_data={"result": str(result)[:1000]},
            reasoning="Tool execution completed, returning result to agent",
            session_id=self.session_id,
        ))

    async def on_handoff(self, context: RunContextWrapper, agent, source) -> None:
        """Multi-agent handoff. Agent A transfers work to Agent B."""
        self.store.save(Event(
            timestamp=now(),
            event_type="decision",
            agent_id=getattr(source, "name", "unknown"),
            action=f"handoff:{getattr(agent, 'name', 'unknown')}",
            input_data={
                "from_agent": getattr(source, "name", "unknown"),
                "to_agent": getattr(agent, "name", "unknown"),
            },
            output_data={},
            reasoning=f"Agent '{getattr(source, 'name', '?')}' handed off work to '{getattr(agent, 'name', '?')}'",
            session_id=self.session_id,
        ))
