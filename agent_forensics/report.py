"""
Forensics Report Generator — Analyzes agent behavior and generates reports.

Reads events from the EventStore to:
1. Reconstruct the timeline (chronological list of actions)
2. Analyze the decision chain (decision -> reasoning -> result)
3. Perform incident analysis (trace error causes)
4. Generate a Markdown forensics report file
"""

from datetime import datetime
from .store import EventStore, Event


def generate_report(store: EventStore, session_id: str) -> str:
    """Analyze all events in a session and generate a Markdown forensics report."""

    events = store.get_session_events(session_id)
    if not events:
        return f"# Forensics Report\n\nNo events found for session `{session_id}`."

    # Classify events
    decisions = [e for e in events if e.event_type == "decision"]
    errors = [e for e in events if e.event_type == "error"]
    tool_calls = [e for e in events if e.event_type in ("tool_call_start", "tool_call_end")]
    final = [e for e in events if e.event_type == "final_decision"]
    context_injections = [e for e in events if e.event_type == "context_injection"]
    prompt_drifts = [e for e in events if e.event_type == "prompt_drift"]
    guardrail_blocks = [e for e in events if e.event_type == "guardrail_block"]
    guardrail_passes = [e for e in events if e.event_type == "guardrail_pass"]

    # Determine incident status
    has_incident = len(errors) > 0 or len(prompt_drifts) > 0 or len(guardrail_blocks) > 0 or any(
        "error" in str(e.output_data).lower() or "fail" in str(e.output_data).lower()
        for e in events
    )

    report = []

    # -- Header --
    report.append("# AI Agent Forensics Report")
    report.append("")
    report.append(f"**Session ID:** `{session_id}`")
    report.append(f"**Agent ID:** `{events[0].agent_id}`")
    report.append(f"**Report Generated:** {datetime.now().isoformat()}")
    report.append(f"**Total Events:** {len(events)}")
    report.append(f"**Incident Detected:** {'YES' if has_incident else 'NO'}")
    report.append("")

    # -- Summary --
    report.append("## Executive Summary")
    report.append("")
    if has_incident:
        report.append("> **An incident was detected.** Errors or failures occurred during agent execution.")
        report.append("> Refer to the timeline and incident analysis below.")
    else:
        report.append("> The agent completed execution normally.")
        report.append("> All decision paths have been recorded.")
    report.append("")

    # -- Timeline --
    report.append("## Timeline")
    report.append("")
    report.append("| # | Timestamp | Type | Action | Detail |")
    report.append("|---|-----------|------|--------|--------|")

    for i, event in enumerate(events, 1):
        # Icon by type
        type_icon = {
            "llm_call_start": "LLM-REQ",
            "llm_call_end": "LLM-RES",
            "tool_call_start": "TOOL-REQ",
            "tool_call_end": "TOOL-RES",
            "decision": "DECISION",
            "final_decision": "FINAL",
            "error": "ERROR",
            "context_injection": "CONTEXT",
            "prompt_state": "PROMPT",
            "prompt_drift": "DRIFT",
            "guardrail_pass": "GUARD-OK",
            "guardrail_block": "GUARD-BLOCK",
        }.get(event.event_type, event.event_type)

        # Extract key information
        detail = _extract_detail(event)

        report.append(
            f"| {i} | {event.timestamp} | {type_icon} | {event.action} | {detail} |"
        )

    report.append("")

    # -- Decision Chain --
    if decisions or final:
        report.append("## Decision Chain")
        report.append("")
        report.append("Each decision made by the agent and its reasoning:")
        report.append("")

        for i, d in enumerate(decisions, 1):
            report.append(f"### Decision {i}: `{d.action}`")
            report.append(f"- **Time:** {d.timestamp}")
            report.append(f"- **Input:** `{_truncate(str(d.input_data), 200)}`")
            report.append(f"- **Reasoning:** {d.reasoning}")
            report.append("")

        if final:
            f = final[-1]
            report.append("### Final Decision")
            report.append(f"- **Time:** {f.timestamp}")
            report.append(f"- **Result:** `{_truncate(str(f.output_data), 300)}`")
            report.append(f"- **Reasoning:** {f.reasoning}")
            report.append("")

    # -- Incident Analysis --
    if has_incident:
        report.append("## Incident Analysis")
        report.append("")

        # Error event details
        if errors:
            report.append("### Errors")
            report.append("")
            for e in errors:
                report.append(f"- **{e.timestamp}** | `{e.action}`")
                report.append(f"  - Error: `{e.output_data}`")
                report.append(f"  - Context: {e.reasoning}")
                report.append("")

        # Find failed tool calls
        failed_tools = [
            e for e in events
            if e.event_type == "tool_call_end"
            and ("error" in str(e.output_data).lower() or "fail" in str(e.output_data).lower())
        ]
        if failed_tools:
            report.append("### Failed Tool Calls")
            report.append("")
            for ft in failed_tools:
                report.append(f"- **{ft.timestamp}** | `{ft.action}`")
                report.append(f"  - Result: `{_truncate(str(ft.output_data), 300)}`")
                report.append("")

        # Causal chain tracing
        report.append("### Causal Chain (Root Cause Analysis)")
        report.append("")
        report.append(_build_causal_chain(events))
        report.append("")

    # -- Prompt Drift Analysis --
    if prompt_drifts:
        report.append("## Prompt Drift Analysis")
        report.append("")
        report.append(f"> **{len(prompt_drifts)} prompt drift(s) detected.** The system prompt changed between agent steps.")
        report.append("")
        for i, pd in enumerate(prompt_drifts, 1):
            report.append(f"### Drift {i}")
            report.append(f"- **Timestamp:** {pd.timestamp}")
            diff = pd.input_data.get("diff", {})
            added = diff.get("added", [])
            removed = diff.get("removed", [])
            if added:
                report.append(f"- **Added:** `{_truncate(str(added), 200)}`")
            if removed:
                report.append(f"- **Removed:** `{_truncate(str(removed), 200)}`")
            report.append("")

    # -- Context Injection Log --
    if context_injections:
        report.append("## Context Injections")
        report.append("")
        report.append(f"{len(context_injections)} external context injection(s) recorded.")
        report.append("")
        report.append("| # | Timestamp | Source | Detail |")
        report.append("|---|-----------|--------|--------|")
        for i, ci in enumerate(context_injections, 1):
            report.append(
                f"| {i} | {ci.timestamp} | {ci.action} | `{_truncate(str(ci.input_data), 100)}` |"
            )
        report.append("")

    # -- Tool Usage Summary --
    report.append("## Tool Usage Summary")
    report.append("")
    tool_starts = [e for e in events if e.event_type == "tool_call_start"]
    if tool_starts:
        report.append("| Tool | Input | Timestamp |")
        report.append("|------|-------|-----------|")
        for ts in tool_starts:
            report.append(
                f"| {ts.action} | `{_truncate(str(ts.input_data), 100)}` | {ts.timestamp} |"
            )
    report.append("")

    # -- Compliance Notes --
    report.append("## Compliance Notes")
    report.append("")
    report.append("- This report supports EU AI Act Article 14 (Human Oversight) requirements.")
    report.append("- All agent decision points have been recorded.")
    report.append(f"- Total events captured: {len(events)}")
    report.append(f"- Decision points: {len(decisions)}")
    report.append(f"- Errors/incidents: {len(errors)}")
    report.append(f"- Prompt drifts: {len(prompt_drifts)}")
    report.append(f"- Context injections: {len(context_injections)}")
    report.append(f"- Guardrail checks: {len(guardrail_passes)} passed, {len(guardrail_blocks)} blocked")
    report.append("")

    return "\n".join(report)


def _extract_detail(event: Event) -> str:
    """Extract key information from an event into a single line."""
    if event.event_type == "llm_call_start":
        messages = event.input_data.get("messages", [])
        if messages:
            last_msg = messages[-1]
            role = last_msg.get("role", "")
            content = last_msg.get("content", "")
            return _truncate(f"[{role}] {content}", 120)
        return _truncate(str(event.input_data), 100)
    elif event.event_type == "llm_call_end":
        return _truncate(event.output_data.get("response", ""), 100)
    elif event.event_type == "final_decision":
        return _truncate(event.output_data.get("response", event.reasoning), 120)
    elif event.event_type in ("tool_call_start", "tool_call_end"):
        data = event.input_data or event.output_data
        return _truncate(str(data), 100)
    elif event.event_type == "decision":
        return _truncate(event.reasoning, 120)
    elif event.event_type == "error":
        return _truncate(str(event.output_data), 100)
    elif event.event_type == "context_injection":
        return _truncate(f"Source: {event.action} — {event.reasoning}", 120)
    elif event.event_type == "prompt_drift":
        diff = event.input_data.get("diff", {})
        added = len(diff.get("added", []))
        removed = len(diff.get("removed", []))
        return _truncate(f"DRIFT: +{added} lines, -{removed} lines changed", 120)
    elif event.event_type == "prompt_state":
        return _truncate("Prompt state recorded", 100)
    elif event.event_type in ("guardrail_pass", "guardrail_block"):
        intent = event.input_data.get("intent", "")
        action = event.input_data.get("action", "")
        allowed = event.input_data.get("allowed", False)
        status = "ALLOWED" if allowed else "BLOCKED"
        return _truncate(f"{status}: intent='{intent}' action='{action}' — {event.reasoning}", 120)
    return _truncate(event.reasoning, 100)


def _truncate(text: str, max_len: int) -> str:
    """Truncate long text and remove characters that break markdown tables."""
    text = text.replace("|", "/").replace("\n", " ")
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def _build_causal_chain(events: list[Event]) -> str:
    """Build a causal chain from the event list."""
    chain_parts = []
    chain_parts.append("```")

    for i, event in enumerate(events):
        indent = ""
        connector = "→"

        if event.event_type == "decision":
            chain_parts.append(f"[DECISION] {event.action}")
            chain_parts.append(f"  Reasoning: {_truncate(event.reasoning, 200)}")
        elif event.event_type == "tool_call_start":
            chain_parts.append(f"  {connector} [TOOL] {event.action}")
            chain_parts.append(f"     Input: {_truncate(str(event.input_data), 150)}")
        elif event.event_type == "tool_call_end":
            result = str(event.output_data)
            is_error = "error" in result.lower() or "fail" in result.lower()
            marker = "*** ERROR ***" if is_error else "OK"
            chain_parts.append(f"     Result: [{marker}] {_truncate(result, 150)}")
        elif event.event_type == "error":
            chain_parts.append(f"  *** ERROR: {_truncate(str(event.output_data), 200)} ***")
        elif event.event_type == "context_injection":
            chain_parts.append(f"[CONTEXT] {event.action}")
            chain_parts.append(f"  Injected: {_truncate(str(event.input_data), 150)}")
        elif event.event_type == "prompt_drift":
            chain_parts.append(f"[*** PROMPT DRIFT ***]")
            diff = event.input_data.get("diff", {})
            if diff.get("added"):
                chain_parts.append(f"  + Added: {_truncate(str(diff['added']), 150)}")
            if diff.get("removed"):
                chain_parts.append(f"  - Removed: {_truncate(str(diff['removed']), 150)}")
        elif event.event_type == "guardrail_block":
            intent = event.input_data.get("intent", "")
            action = event.input_data.get("action", "")
            chain_parts.append(f"[*** GUARDRAIL BLOCKED ***] {action}")
            chain_parts.append(f"  Intent: {intent} — {_truncate(event.reasoning, 150)}")
        elif event.event_type == "guardrail_pass":
            action = event.input_data.get("action", "")
            chain_parts.append(f"[GUARDRAIL OK] {action}")
        elif event.event_type == "final_decision":
            chain_parts.append(f"[FINAL] {_truncate(str(event.output_data), 200)}")

    chain_parts.append("```")
    return "\n".join(chain_parts)


def save_report(store: EventStore, session_id: str, output_dir: str = ".") -> str:
    """Generate and save the report as a Markdown file. Returns the file path."""
    report_content = generate_report(store, session_id)
    filename = f"{output_dir}/forensics-report-{session_id}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"[Forensics] Report saved: {filename}")
    return filename


def save_pdf(store: EventStore, session_id: str, output_dir: str = ".") -> str:
    """Save the report as a PDF. Uses fpdf2 (pure Python, no external dependencies)."""
    from fpdf import FPDF

    events = store.get_session_events(session_id)
    if not events:
        return ""

    decisions = [e for e in events if e.event_type == "decision"]
    errors = [e for e in events if e.event_type == "error"]
    has_incident = len(errors) > 0 or any(
        "error" in str(e.output_data).lower() or "fail" in str(e.output_data).lower()
        for e in events
    )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    # Add Unicode font
    pdf.add_font("NotoSans", "", "/System/Library/Fonts/AppleSDGothicNeo.ttc", uni=True)
    pdf.add_font("NotoSans", "B", "/System/Library/Fonts/AppleSDGothicNeo.ttc", uni=True)
    pdf.add_page()

    # -- Header --
    pdf.set_font("NotoSans", "B", 20)
    pdf.cell(0, 12, "AI Agent Forensics Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(26, 115, 232)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("NotoSans", "", 10)
    pdf.cell(0, 6, f"Session: {session_id}  |  Agent: {events[0].agent_id}  |  Events: {len(events)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Generated: {datetime.now().isoformat()}",  new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # -- Incident status banner --
    if has_incident:
        pdf.set_fill_color(254, 243, 242)
        pdf.set_text_color(217, 48, 37)
        pdf.set_font("NotoSans", "B", 11)
        pdf.cell(0, 10, "  INCIDENT DETECTED", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.set_fill_color(237, 247, 237)
        pdf.set_text_color(52, 168, 83)
        pdf.set_font("NotoSans", "B", 11)
        pdf.cell(0, 10, "  OK - No incidents", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # -- Timeline --
    pdf.set_font("NotoSans", "B", 14)
    pdf.cell(0, 10, "Timeline", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Table header
    pdf.set_font("NotoSans", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    col_widths = [8, 22, 22, 35, 103]
    headers = ["#", "Time", "Type", "Action", "Detail"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, h, border=1, fill=True)
    pdf.ln()

    # Table body
    pdf.set_font("NotoSans", "", 7)
    type_labels = {
        "llm_call_start": "LLM-REQ", "llm_call_end": "LLM-RES",
        "tool_call_start": "TOOL-REQ", "tool_call_end": "TOOL-RES",
        "decision": "DECISION", "final_decision": "FINAL", "error": "ERROR",
    }

    for i, event in enumerate(events, 1):
        time_str = event.timestamp.split("T")[1].split("+")[0][:12]
        type_str = type_labels.get(event.event_type, event.event_type)
        detail = _truncate(_extract_detail_plain(event), 90)

        # Error rows get red background
        if event.event_type == "error":
            pdf.set_fill_color(254, 243, 242)
            fill = True
        elif event.event_type == "decision":
            pdf.set_fill_color(232, 240, 254)
            fill = True
        elif event.event_type == "final_decision":
            pdf.set_fill_color(243, 232, 254)
            fill = True
        else:
            fill = False

        pdf.cell(col_widths[0], 6, str(i), border=1, fill=fill)
        pdf.cell(col_widths[1], 6, time_str, border=1, fill=fill)
        pdf.cell(col_widths[2], 6, type_str, border=1, fill=fill)
        pdf.cell(col_widths[3], 6, _truncate(event.action, 28), border=1, fill=fill)
        pdf.cell(col_widths[4], 6, detail, border=1, fill=fill)
        pdf.ln()

    pdf.ln(6)

    # -- Decision Chain --
    if decisions:
        pdf.set_font("NotoSans", "B", 14)
        pdf.cell(0, 10, "Decision Chain", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        for i, d in enumerate(decisions, 1):
            pdf.set_font("NotoSans", "B", 9)
            pdf.cell(0, 6, f"Decision {i}: {d.action}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("NotoSans", "", 8)
            pdf.cell(0, 5, f"Time: {d.timestamp}", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 5, f"Reasoning: {_truncate(d.reasoning, 200)}")
            pdf.ln(3)

    # -- Incident Analysis --
    if has_incident:
        pdf.set_font("NotoSans", "B", 14)
        pdf.set_text_color(217, 48, 37)
        pdf.cell(0, 10, "Incident Analysis", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        pdf.set_font("NotoSans", "", 8)
        for e in errors:
            pdf.multi_cell(0, 5, f"[{e.timestamp}] {e.action}: {_truncate(str(e.output_data), 200)}")
            pdf.ln(2)

        failed_tools = [
            e for e in events
            if e.event_type == "tool_call_end"
            and ("error" in str(e.output_data).lower() or "fail" in str(e.output_data).lower())
        ]
        for ft in failed_tools:
            pdf.multi_cell(0, 5, f"Failed: [{ft.timestamp}] {_truncate(str(ft.output_data), 200)}")
            pdf.ln(2)

    # -- Compliance --
    pdf.ln(4)
    pdf.set_font("NotoSans", "B", 14)
    pdf.cell(0, 10, "Compliance Notes", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("NotoSans", "", 9)
    pdf.multi_cell(0, 5,
        f"This report supports EU AI Act Article 14 (Human Oversight) requirements.\n"
        f"Total events captured: {len(events)}\n"
        f"Decision points: {len(decisions)}\n"
        f"Errors: {len(errors)}"
    )

    filename = f"{output_dir}/forensics-report-{session_id}.pdf"
    pdf.output(filename)
    print(f"[Forensics] PDF saved: {filename}")
    return filename


def _extract_detail_plain(event: Event) -> str:
    """For PDF — extract plain text without markdown syntax."""
    if event.event_type == "llm_call_start":
        messages = event.input_data.get("messages", [])
        if messages:
            last = messages[-1]
            return f"[{last.get('role', '')}] {last.get('content', '')}"
        return str(event.input_data)
    elif event.event_type in ("final_decision", "llm_call_end"):
        return event.output_data.get("response", event.reasoning)
    elif event.event_type == "decision":
        return event.reasoning
    elif event.event_type in ("tool_call_start", "tool_call_end"):
        data = event.input_data or event.output_data
        return str(data)
    elif event.event_type == "error":
        return str(event.output_data)
    return event.reasoning


if __name__ == "__main__":
    import sys

    store = EventStore("forensics.db")
    sessions = store.get_all_sessions()

    if not sessions:
        print("No saved sessions found. Run agent.py first.")
    else:
        fmt = sys.argv[1] if len(sys.argv) > 1 else "all"
        for sid in sessions:
            save_report(store, sid)
            if fmt in ("pdf", "all"):
                save_pdf(store, sid)
