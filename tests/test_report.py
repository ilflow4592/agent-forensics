"""Tests for report generation — Markdown output with all event types and edge cases."""

import pytest

from agent_forensics.core import Forensics
from agent_forensics.report import generate_report, save_report


class TestEmptySession:
    def test_empty_session_report(self, store):
        report = generate_report(store, "nonexistent")
        assert "No events found" in report
        assert "nonexistent" in report


class TestBasicReport:
    def test_report_contains_header(self, forensics):
        forensics.decision("search", reasoning="user request")
        forensics.finish("done")
        report = forensics.report()

        assert "# AI Agent Forensics Report" in report
        assert "test-session" in report
        assert "test-agent" in report
        assert "Total Events:" in report

    def test_report_contains_timeline(self, forensics):
        forensics.decision("act")
        report = forensics.report()
        assert "## Timeline" in report
        assert "DECISION" in report

    def test_report_contains_decision_chain(self, forensics):
        forensics.decision("choose_a", reasoning="Reason A")
        forensics.decision("choose_b", reasoning="Reason B")
        report = forensics.report()
        assert "## Decision Chain" in report
        assert "choose_a" in report
        assert "Reason A" in report

    def test_report_contains_compliance_notes(self, forensics):
        forensics.decision("act")
        report = forensics.report()
        assert "## Compliance Notes" in report
        assert "EU AI Act" in report


class TestIncidentReport:
    def test_incident_detected_with_error(self, forensics):
        forensics.error("api_failure", output={"msg": "500 error"})
        report = forensics.report()
        assert "Incident Detected:** YES" in report
        assert "## Incident Analysis" in report
        assert "api_failure" in report

    def test_incident_detected_with_tool_failure(self, forensics):
        forensics.tool_call("bad_api", output={"error": "connection refused"})
        report = forensics.report()
        assert "Incident Detected:** YES" in report

    def test_no_incident_on_clean_run(self, forensics):
        forensics.decision("search")
        forensics.tool_call("api", output={"data": "ok"})
        forensics.finish("all good")
        report = forensics.report()
        assert "Incident Detected:** NO" in report


class TestAllEventTypes:
    """모든 event type이 report에 포함되는지 검증."""

    def test_llm_call_in_timeline(self, forensics):
        forensics.llm_call(
            input={"messages": [{"role": "user", "content": "hello"}]},
            output="Hi there",
        )
        report = forensics.report()
        assert "LLM-REQ" in report
        assert "LLM-RES" in report

    def test_tool_call_in_timeline(self, forensics):
        forensics.tool_call("search_api", input={"q": "test"}, output={"results": []})
        report = forensics.report()
        assert "TOOL-REQ" in report
        assert "TOOL-RES" in report

    def test_guardrail_in_timeline(self, forensics):
        forensics.guardrail(intent="buy", action="purchase", allowed=True, reason="ok")
        forensics.guardrail(intent="delete", action="rm_data", allowed=False, reason="blocked")
        report = forensics.report()
        assert "GUARD-OK" in report
        assert "GUARD-BLOCK" in report

    def test_context_injection_section(self, forensics):
        forensics.context_injection("vector_db", content={"doc": "relevant text"})
        report = forensics.report()
        assert "## Context Injections" in report
        assert "vector_db" in report

    def test_prompt_drift_section(self, forensics):
        forensics.prompt_state("Original prompt")
        forensics.prompt_state("Changed prompt")
        report = forensics.report()
        assert "## Prompt Drift Analysis" in report
        assert "DRIFT" in report

    def test_final_decision_in_chain(self, forensics):
        forensics.decision("step1")
        forensics.finish("final answer", reasoning="done")
        report = forensics.report()
        assert "### Final Decision" in report
        assert "final answer" in report


class TestFailureClassificationInReport:
    def test_failure_section_appears(self, forensics):
        # Create a scenario that triggers MISSING_APPROVAL
        forensics.decision("purchase item", reasoning="buying")
        forensics.finish("bought it")
        report = forensics.report()
        assert "## Failure Classification" in report
        assert "MISSING_APPROVAL" in report


class TestToolUsageSummary:
    def test_tool_usage_listed(self, forensics):
        forensics.tool_call("api_a", input={"x": 1})
        forensics.tool_call("api_b", input={"y": 2})
        report = forensics.report()
        assert "## Tool Usage Summary" in report
        assert "tool:api_a" in report
        assert "tool:api_b" in report


class TestSaveReport:
    def test_save_markdown_creates_file(self, tmp_db, tmp_path):
        f = Forensics(session="save-test", db_path=tmp_db)
        f.decision("act")
        path = save_report(f.store, "save-test", output_dir=str(tmp_path))
        assert path.endswith(".md")
        with open(path) as fh:
            content = fh.read()
        assert "# AI Agent Forensics Report" in content

    def test_save_markdown_via_forensics(self, tmp_db, tmp_path):
        f = Forensics(session="md-test", db_path=tmp_db)
        f.decision("act")
        path = f.save_markdown(str(tmp_path))
        assert path.endswith(".md")


class TestReportEdgeCases:
    def test_long_reasoning_truncated(self, forensics):
        forensics.decision("act", reasoning="x" * 500)
        report = forensics.report()
        # Should not crash; truncation happens in timeline detail
        assert "act" in report

    def test_special_chars_in_detail(self, forensics):
        forensics.decision("act", reasoning="reason|with|pipes\nand newlines")
        report = forensics.report()
        # _truncate replaces pipes and newlines in the detail column
        assert "reason/with/pipes and newlines" in report

    def test_many_events(self, forensics):
        for i in range(50):
            forensics.decision(f"step_{i}")
        report = forensics.report()
        assert "step_49" in report


class TestMultiAgentReport:
    def test_multi_agent_section_appears(self, tmp_db):
        f1 = Forensics(session="multi", agent="planner", db_path=tmp_db)
        f1.decision("plan")
        f1.handoff("executor", reasoning="Delegating task")

        f2 = Forensics(session="multi", agent="executor", db_path=tmp_db)
        f2.decision("execute")
        f2.finish("done")

        report = f1.report()
        assert "## Multi-Agent Analysis" in report
        assert "### Handoff Flow" in report
        assert "planner" in report
        assert "executor" in report

    def test_per_agent_breakdown_table(self, tmp_db):
        f1 = Forensics(session="multi2", agent="agent-a", db_path=tmp_db)
        f1.decision("search")

        f2 = Forensics(session="multi2", agent="agent-b", db_path=tmp_db)
        f2.decision("act")

        report = f1.report()
        assert "### Per-Agent Breakdown" in report
        assert "agent-a" in report
        assert "agent-b" in report

    def test_handoff_in_timeline(self, tmp_db):
        f = Forensics(session="htest", agent="a", db_path=tmp_db)
        f.handoff("b", reasoning="delegate")
        report = f.report()
        assert "HANDOFF" in report

    def test_single_agent_no_multi_section(self, forensics):
        forensics.decision("act")
        forensics.finish("done")
        report = forensics.report()
        assert "## Multi-Agent Analysis" not in report
