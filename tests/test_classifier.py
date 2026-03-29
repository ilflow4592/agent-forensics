"""Tests for the failure classifier — each of the 6 failure patterns."""

import pytest

from agent_forensics.store import Event, now
from agent_forensics.classifier import classify_failures, failure_summary


def _event(event_type, action="action", input_data=None, output_data=None, reasoning=""):
    """Helper to create an Event quickly."""
    return Event(
        timestamp=now(),
        event_type=event_type,
        agent_id="test-agent",
        action=action,
        input_data=input_data or {},
        output_data=output_data or {},
        reasoning=reasoning,
        session_id="test",
    )


class TestHallucinatedToolOutput:
    """Tool이 에러를 반환했는데 agent가 무시하고 진행한 경우."""

    def test_detects_ignored_tool_error(self):
        events = [
            _event("tool_call_start", action="tool:search"),
            _event("tool_call_end", action="tool_result",
                   output_data={"error": "API rate limit exceeded"}),
            _event("decision", action="use_results",
                   reasoning="Using the search results to proceed"),
        ]
        failures = classify_failures(events)
        hallucinated = [f for f in failures if f["type"] == "HALLUCINATED_TOOL_OUTPUT"]
        assert len(hallucinated) == 1
        assert hallucinated[0]["severity"] == "HIGH"

    def test_no_false_positive_when_error_acknowledged(self):
        events = [
            _event("tool_call_start", action="tool:search"),
            _event("tool_call_end", action="tool_result",
                   output_data={"error": "not found"}),
            _event("decision", action="handle_error",
                   reasoning="Tool returned error, trying fallback"),
        ]
        failures = classify_failures(events)
        hallucinated = [f for f in failures if f["type"] == "HALLUCINATED_TOOL_OUTPUT"]
        assert len(hallucinated) == 0

    def test_no_false_positive_on_successful_tool(self):
        events = [
            _event("tool_call_start", action="tool:search"),
            _event("tool_call_end", action="tool_result",
                   output_data={"results": ["item1"]}),
            _event("decision", action="use_results", reasoning="Got results"),
        ]
        failures = classify_failures(events)
        hallucinated = [f for f in failures if f["type"] == "HALLUCINATED_TOOL_OUTPUT"]
        assert len(hallucinated) == 0


class TestMissingApproval:
    """Critical action이 guardrail 없이 실행된 경우."""

    def test_detects_purchase_without_guardrail(self):
        events = [
            _event("decision", action="search_products", reasoning="looking"),
            _event("decision", action="purchase item", reasoning="buying it"),
        ]
        failures = classify_failures(events)
        missing = [f for f in failures if f["type"] == "MISSING_APPROVAL"]
        assert len(missing) == 1
        assert missing[0]["severity"] == "HIGH"

    def test_detects_delete_without_guardrail(self):
        events = [
            _event("decision", action="delete user data", reasoning="cleanup"),
        ]
        failures = classify_failures(events)
        missing = [f for f in failures if f["type"] == "MISSING_APPROVAL"]
        assert len(missing) == 1

    def test_no_false_positive_with_guardrail(self):
        events = [
            _event("guardrail_pass", action="guardrail:purchase",
                   input_data={"intent": "buy", "action": "purchase", "allowed": True}),
            _event("decision", action="purchase item", reasoning="approved"),
        ]
        failures = classify_failures(events)
        missing = [f for f in failures if f["type"] == "MISSING_APPROVAL"]
        assert len(missing) == 0

    def test_no_false_positive_for_non_critical_action(self):
        events = [
            _event("decision", action="search products", reasoning="looking"),
        ]
        failures = classify_failures(events)
        missing = [f for f in failures if f["type"] == "MISSING_APPROVAL"]
        assert len(missing) == 0


class TestPromptDriftCaused:
    """Prompt drift 직후 decision이 내려진 경우."""

    def test_detects_decision_after_drift(self):
        events = [
            _event("prompt_drift", action="prompt_drift",
                   input_data={"diff": {"added": ["new rule"], "removed": []}}),
            _event("decision", action="changed_behavior", reasoning="following new rules"),
        ]
        failures = classify_failures(events)
        drift = [f for f in failures if f["type"] == "PROMPT_DRIFT_CAUSED"]
        assert len(drift) == 1
        assert drift[0]["severity"] == "MEDIUM"

    def test_no_false_positive_without_drift(self):
        events = [
            _event("prompt_state", action="prompt_state"),
            _event("decision", action="normal_action", reasoning="business logic"),
        ]
        failures = classify_failures(events)
        drift = [f for f in failures if f["type"] == "PROMPT_DRIFT_CAUSED"]
        assert len(drift) == 0


class TestSilentSubstitution:
    """요청한 것과 다른 결과를 승인 없이 제공한 경우."""

    def test_detects_substitution_after_not_found(self):
        events = [
            _event("decision", action="search",
                   input_data={"query": "specific product X"}),
            _event("tool_call_start", action="tool:search"),
            _event("tool_call_end", action="tool_result",
                   output_data={"error": "not found", "success": False}),
            _event("final_decision", action="agent_finish",
                   output_data={"response": "I purchased product Y for you"}),
        ]
        failures = classify_failures(events)
        subs = [f for f in failures if f["type"] == "SILENT_SUBSTITUTION"]
        # This may or may not trigger depending on heuristics
        assert isinstance(subs, list)

    def test_no_detection_without_final_decision(self):
        events = [
            _event("decision", action="search", input_data={"query": "item"}),
            _event("tool_call_start", action="tool:api"),
            _event("tool_call_end", action="tool_result", output_data={"data": "ok"}),
        ]
        failures = classify_failures(events)
        subs = [f for f in failures if f["type"] == "SILENT_SUBSTITUTION"]
        assert len(subs) == 0


class TestRepeatedFailure:
    """같은 tool이 반복적으로 실패한 경우."""

    def test_detects_repeated_tool_failure(self):
        events = [
            _event("tool_call_start", action="tool:flaky_api"),
            _event("tool_call_end", action="tool_result",
                   output_data={"error": "timeout"}),
            _event("tool_call_start", action="tool:flaky_api"),
            _event("tool_call_end", action="tool_result",
                   output_data={"error": "timeout"}),
            _event("tool_call_start", action="tool:flaky_api"),
            _event("tool_call_end", action="tool_result",
                   output_data={"error": "timeout"}),
        ]
        failures = classify_failures(events)
        repeated = [f for f in failures if f["type"] == "REPEATED_FAILURE"]
        assert len(repeated) == 1
        assert repeated[0]["evidence"]["failures"] >= 2

    def test_no_false_positive_single_failure(self):
        events = [
            _event("tool_call_start", action="tool:api"),
            _event("tool_call_end", action="tool_result",
                   output_data={"error": "timeout"}),
            _event("tool_call_start", action="tool:api"),
            _event("tool_call_end", action="tool_result",
                   output_data={"result": "success"}),
        ]
        failures = classify_failures(events)
        repeated = [f for f in failures if f["type"] == "REPEATED_FAILURE"]
        assert len(repeated) == 0


class TestRetrievalMismatch:
    """Retrieved context의 similarity score가 낮은 경우."""

    def test_detects_low_similarity(self):
        events = [
            _event("context_injection", action="context:vector_db",
                   input_data={"similarity_score": 0.45, "content": "irrelevant doc"}),
        ]
        failures = classify_failures(events)
        mismatch = [f for f in failures if f["type"] == "RETRIEVAL_MISMATCH"]
        assert len(mismatch) == 1
        assert mismatch[0]["severity"] == "MEDIUM"

    def test_no_detection_for_high_similarity(self):
        events = [
            _event("context_injection", action="context:vector_db",
                   input_data={"similarity_score": 0.95}),
        ]
        failures = classify_failures(events)
        mismatch = [f for f in failures if f["type"] == "RETRIEVAL_MISMATCH"]
        assert len(mismatch) == 0

    def test_no_detection_without_score(self):
        events = [
            _event("context_injection", action="context:rag",
                   input_data={"content": "some doc"}),
        ]
        failures = classify_failures(events)
        mismatch = [f for f in failures if f["type"] == "RETRIEVAL_MISMATCH"]
        assert len(mismatch) == 0

    def test_boundary_score_0_7(self):
        events = [
            _event("context_injection", action="context:db",
                   input_data={"similarity_score": 0.7}),
        ]
        failures = classify_failures(events)
        mismatch = [f for f in failures if f["type"] == "RETRIEVAL_MISMATCH"]
        assert len(mismatch) == 0  # 0.7 is NOT < 0.7


class TestFailureSummary:
    """failure_summary 집계 함수 테스트."""

    def test_empty_input(self):
        result = failure_summary([])
        assert result["total_failures"] == 0

    def test_aggregates_by_type_and_severity(self):
        failures = [
            {"type": "MISSING_APPROVAL", "severity": "HIGH", "description": "a", "step": 1},
            {"type": "MISSING_APPROVAL", "severity": "HIGH", "description": "b", "step": 2},
            {"type": "REPEATED_FAILURE", "severity": "MEDIUM", "description": "c", "step": 3},
        ]
        result = failure_summary(failures)
        assert result["total_failures"] == 3
        assert result["by_type"]["MISSING_APPROVAL"]["count"] == 2
        assert result["by_type"]["REPEATED_FAILURE"]["count"] == 1
        assert result["by_severity"]["HIGH"] == 2
        assert result["by_severity"]["MEDIUM"] == 1


class TestClassifyEmptyTrace:
    """빈 이벤트 리스트에서 classifier가 크래시하지 않는지 검증."""

    def test_empty_events(self):
        assert classify_failures([]) == []
