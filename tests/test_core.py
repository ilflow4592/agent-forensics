"""Tests for Forensics — the main interface class."""

import pytest

from agent_forensics.core import Forensics
from agent_forensics.store import Event


class TestDecision:
    def test_records_decision_event(self, forensics):
        eid = forensics.decision("search_products", input={"q": "mouse"}, reasoning="User asked")
        assert eid

        events = forensics.events()
        assert len(events) == 1
        assert events[0].event_type == "decision"
        assert events[0].action == "search_products"
        assert events[0].input_data == {"q": "mouse"}
        assert events[0].reasoning == "User asked"

    def test_decision_defaults(self, forensics):
        forensics.decision("act")
        e = forensics.events()[0]
        assert e.input_data == {}
        assert e.reasoning == ""


class TestToolCall:
    def test_records_start_and_end(self, forensics):
        forensics.tool_call("search_api", input={"q": "mouse"}, output={"results": []})
        events = forensics.events()
        assert len(events) == 2
        assert events[0].event_type == "tool_call_start"
        assert events[0].action == "tool:search_api"
        assert events[1].event_type == "tool_call_end"
        assert events[1].action == "tool_result"
        assert events[1].output_data == {"results": []}

    def test_tool_call_defaults(self, forensics):
        forensics.tool_call("my_tool")
        events = forensics.events()
        assert events[0].input_data == {}
        assert events[1].output_data == {}


class TestLlmCall:
    def test_records_llm_start_and_end(self, forensics):
        forensics.llm_call(
            input={"messages": [{"role": "user", "content": "hi"}]},
            output="Hello!",
            model="gpt-4o",
            temperature=0.0,
            seed=42,
        )
        events = forensics.events()
        assert len(events) == 2
        assert events[0].event_type == "llm_call_start"
        assert events[0].input_data["_model_config"] == {
            "model": "gpt-4o",
            "temperature": 0.0,
            "seed": 42,
        }
        assert events[1].event_type == "llm_call_end"
        assert events[1].output_data == {"response": "Hello!"}

    def test_llm_call_without_model_config(self, forensics):
        forensics.llm_call(output="response")
        e = forensics.events()[0]
        assert "_model_config" not in e.input_data


class TestError:
    def test_records_error(self, forensics):
        forensics.error("purchase_failed", output={"reason": "Out of stock"}, reasoning="API error")
        e = forensics.events()[0]
        assert e.event_type == "error"
        assert e.action == "purchase_failed"
        assert e.output_data == {"reason": "Out of stock"}

    def test_error_default_reasoning(self, forensics):
        forensics.error("timeout")
        e = forensics.events()[0]
        assert "timeout" in e.reasoning


class TestFinish:
    def test_records_final_decision(self, forensics):
        forensics.finish("Here is your answer", reasoning="Task complete")
        e = forensics.events()[0]
        assert e.event_type == "final_decision"
        assert e.action == "agent_finish"
        assert e.output_data == {"response": "Here is your answer"}

    def test_finish_defaults(self, forensics):
        forensics.finish()
        e = forensics.events()[0]
        assert e.output_data == {"response": ""}


class TestGuardrail:
    def test_guardrail_pass(self, forensics):
        forensics.guardrail(intent="check price", action="purchase", allowed=True, reason="Under budget")
        e = forensics.events()[0]
        assert e.event_type == "guardrail_pass"
        assert e.action == "guardrail:purchase"
        assert e.input_data["allowed"] is True

    def test_guardrail_block(self, forensics):
        forensics.guardrail(intent="check price", action="purchase", allowed=False, reason="Over budget")
        e = forensics.events()[0]
        assert e.event_type == "guardrail_block"
        assert e.input_data["allowed"] is False

    def test_guardrail_default_reason(self, forensics):
        forensics.guardrail(intent="intent", action="act", allowed=True)
        e = forensics.events()[0]
        assert "allowed" in e.reasoning.lower()


class TestContextInjection:
    def test_records_context(self, forensics):
        forensics.context_injection(
            "vector_db",
            content={"chunks": ["doc1", "doc2"], "similarity_score": 0.92},
            reasoning="RAG retrieval",
        )
        e = forensics.events()[0]
        assert e.event_type == "context_injection"
        assert e.action == "context:vector_db"
        assert e.input_data["similarity_score"] == 0.92

    def test_context_injection_defaults(self, forensics):
        forensics.context_injection("memory")
        e = forensics.events()[0]
        assert e.input_data == {}
        assert "memory" in e.reasoning


class TestPromptState:
    def test_initial_prompt_no_drift(self, forensics):
        forensics.prompt_state("You are a helpful assistant.")
        e = forensics.events()[0]
        assert e.event_type == "prompt_state"
        assert e.input_data["prompt_changed"] is False

    def test_same_prompt_no_drift(self, forensics):
        forensics.prompt_state("Same prompt")
        forensics.prompt_state("Same prompt")
        events = forensics.events()
        assert events[1].event_type == "prompt_state"
        assert events[1].input_data["prompt_changed"] is False

    def test_changed_prompt_drift_detected(self, forensics):
        forensics.prompt_state("Original prompt")
        forensics.prompt_state("Modified prompt with new instructions")
        events = forensics.events()
        assert events[1].event_type == "prompt_drift"
        assert events[1].input_data["prompt_changed"] is True
        assert "diff" in events[1].input_data
        assert "DRIFT" in events[1].reasoning

    def test_drift_diff_contains_added_and_removed(self, forensics):
        forensics.prompt_state("Line A\nLine B")
        forensics.prompt_state("Line A\nLine C")
        drift = forensics.events()[1]
        diff = drift.input_data["diff"]
        assert "Line C" in diff["added"]
        assert "Line B" in diff["removed"]

    def test_prompt_state_with_metadata(self, forensics):
        forensics.prompt_state("prompt", metadata={"version": 2})
        e = forensics.events()[0]
        assert e.input_data["metadata"] == {"version": 2}


class TestRecord:
    def test_generic_record(self, forensics):
        forensics.record("custom_type", "custom_action", input={"k": "v"}, output={"r": 1}, reasoning="why")
        e = forensics.events()[0]
        assert e.event_type == "custom_type"
        assert e.action == "custom_action"


class TestClassify:
    def test_classify_returns_list(self, forensics):
        forensics.decision("search", reasoning="looking")
        result = forensics.classify()
        assert isinstance(result, list)

    def test_classify_custom_session(self, tmp_db):
        f1 = Forensics(session="s1", db_path=tmp_db)
        f1.decision("purchase item", reasoning="buy it")
        f2 = Forensics(session="s2", db_path=tmp_db)
        # classify s1 from f2
        result = f2.classify(session_id="s1")
        assert isinstance(result, list)


class TestFailureStats:
    def test_failure_stats_structure(self, forensics):
        forensics.decision("act")
        stats = forensics.failure_stats()
        assert "total_failures" in stats
        assert "by_type" in stats
        assert "by_severity" in stats


class TestReplayConfig:
    def test_get_replay_config(self, forensics):
        forensics.llm_call(
            input={"messages": [{"role": "user", "content": "hi"}]},
            output="Hello",
            model="gpt-4o",
            temperature=0,
            seed=42,
        )
        forensics.tool_call("search", output={"items": [1]})
        forensics.finish("done")

        config = forensics.get_replay_config()
        assert config["model_config"]["model"] == "gpt-4o"
        assert config["model_config"]["seed"] == 42
        assert config["total_events"] > 0
        assert len(config["steps"]) == config["total_events"]
        assert "tool_result" in config["tool_responses"]


class TestReplayDiff:
    def test_matching_sessions(self, tmp_db):
        f1 = Forensics(session="orig", db_path=tmp_db)
        f1.decision("act_a")
        f1.finish("result")

        f2 = Forensics(session="replay", db_path=tmp_db)
        f2.decision("act_a")
        f2.finish("result")

        diff = f1.replay_diff("orig", "replay")
        assert diff["matching"] is True
        assert diff["divergences"] == []

    def test_diverged_sessions(self, tmp_db):
        f1 = Forensics(session="orig2", db_path=tmp_db)
        f1.decision("act_a")
        f1.finish("result_a")

        f2 = Forensics(session="replay2", db_path=tmp_db)
        f2.decision("act_b")
        f2.finish("result_b")

        diff = f1.replay_diff("orig2", "replay2")
        assert diff["matching"] is False
        assert len(diff["divergences"]) > 0

    def test_extra_steps_in_replay(self, tmp_db):
        f1 = Forensics(session="short", db_path=tmp_db)
        f1.decision("only_one")

        f2 = Forensics(session="long", db_path=tmp_db)
        f2.decision("only_one")
        f2.decision("extra")
        f2.finish("done")

        diff = f1.replay_diff("short", "long")
        assert diff["matching"] is False
        extra = [d for d in diff["divergences"] if d["type"] == "extra_in_replay"]
        assert len(extra) > 0


class TestSessionsAndEvents:
    def test_events_returns_current_session(self, forensics):
        forensics.decision("a")
        forensics.decision("b")
        assert len(forensics.events()) == 2

    def test_sessions_list(self, tmp_db):
        f1 = Forensics(session="s1", db_path=tmp_db)
        f1.decision("x")
        f2 = Forensics(session="s2", db_path=tmp_db)
        f2.decision("y")
        assert set(f1.sessions()) == {"s1", "s2"}
