"""
Failure Classifier — Auto-labels common failure modes in agent traces.

Analyzes event sequences and detects patterns like:
- Instruction conflicts
- Hallucinated tool outputs
- Missing approvals
- Prompt drift influence
- Silent substitutions
- Retrieval mismatches

Rule-based in v0.3. LLM-based classification planned for v0.4+.
"""

from .store import Event


# Failure type definitions
FAILURE_TYPES = {
    "INSTRUCTION_CONFLICT": "Multiple conflicting priorities detected in agent instructions",
    "HALLUCINATED_TOOL_OUTPUT": "Agent proceeded as if tool succeeded when it actually failed",
    "MISSING_APPROVAL": "Critical action taken without a guardrail check",
    "PROMPT_DRIFT_CAUSED": "Decision made immediately after prompt drift — potentially influenced by changed instructions",
    "SILENT_SUBSTITUTION": "Final output differs from original user request without explicit approval",
    "RETRIEVAL_MISMATCH": "Retrieved context may not match the original query intent",
    "REPEATED_FAILURE": "Agent retried the same failing action multiple times without changing approach",
}


def classify_failures(events: list[Event]) -> list[dict]:
    """Analyze events and return a list of detected failure patterns.

    Returns:
        List of dicts: [{type, severity, description, evidence, step}]
    """
    failures = []

    failures.extend(_detect_hallucinated_tool_output(events))
    failures.extend(_detect_missing_approval(events))
    failures.extend(_detect_prompt_drift_caused(events))
    failures.extend(_detect_silent_substitution(events))
    failures.extend(_detect_repeated_failure(events))
    failures.extend(_detect_retrieval_mismatch(events))

    return failures


def _detect_hallucinated_tool_output(events: list[Event]) -> list[dict]:
    """Detect: tool returned error/empty, but agent proceeded as if it succeeded."""
    failures = []

    for i, event in enumerate(events):
        if event.event_type != "tool_call_end":
            continue

        result = str(event.output_data).lower()
        is_error = "error" in result or "fail" in result or "not found" in result

        if not is_error:
            continue

        # Check if the next decision ignores the error
        for j in range(i + 1, min(i + 4, len(events))):
            next_event = events[j]
            if next_event.event_type == "decision":
                # Agent made a decision after a tool error — did it acknowledge the error?
                reasoning = next_event.reasoning.lower()
                if "error" not in reasoning and "fail" not in reasoning and "retry" not in reasoning and "not found" not in reasoning:
                    failures.append({
                        "type": "HALLUCINATED_TOOL_OUTPUT",
                        "severity": "HIGH",
                        "description": f"Tool returned an error but agent proceeded without acknowledging it",
                        "evidence": {
                            "tool_result": str(event.output_data)[:200],
                            "next_decision": next_event.action,
                            "next_reasoning": next_event.reasoning[:200],
                        },
                        "step": i + 1,
                    })
                break

    return failures


def _detect_missing_approval(events: list[Event]) -> list[dict]:
    """Detect: critical action (purchase, delete, send) without a preceding guardrail check."""
    failures = []
    critical_keywords = ["purchase", "buy", "delete", "remove", "send", "transfer", "pay", "cancel"]

    for i, event in enumerate(events):
        if event.event_type != "decision":
            continue

        action_lower = event.action.lower()
        is_critical = any(kw in action_lower for kw in critical_keywords)
        if not is_critical:
            continue

        # Look backward for a guardrail check
        has_guardrail = False
        for j in range(max(0, i - 5), i):
            if events[j].event_type in ("guardrail_pass", "guardrail_block"):
                has_guardrail = True
                break

        if not has_guardrail:
            failures.append({
                "type": "MISSING_APPROVAL",
                "severity": "HIGH",
                "description": f"Critical action '{event.action}' taken without guardrail check",
                "evidence": {
                    "action": event.action,
                    "reasoning": event.reasoning[:200],
                },
                "step": i + 1,
            })

    return failures


def _detect_prompt_drift_caused(events: list[Event]) -> list[dict]:
    """Detect: decision made immediately after a prompt drift event."""
    failures = []

    for i, event in enumerate(events):
        if event.event_type != "prompt_drift":
            continue

        # Find the next decision after the drift
        for j in range(i + 1, min(i + 5, len(events))):
            next_event = events[j]
            if next_event.event_type == "decision":
                failures.append({
                    "type": "PROMPT_DRIFT_CAUSED",
                    "severity": "MEDIUM",
                    "description": f"Decision '{next_event.action}' made right after prompt drift — may be influenced by changed instructions",
                    "evidence": {
                        "drift_diff": event.input_data.get("diff", {}),
                        "decision": next_event.action,
                        "reasoning": next_event.reasoning[:200],
                    },
                    "step": j + 1,
                })
                break

    return failures


def _detect_silent_substitution(events: list[Event]) -> list[dict]:
    """Detect: final output doesn't match what the user originally asked for."""
    failures = []

    # Find the first user input
    first_input = None
    for event in events:
        if event.event_type == "decision" and event.input_data:
            first_input = str(event.input_data).lower()
            break
        if event.event_type == "llm_call_start":
            messages = event.input_data.get("messages", [])
            for msg in messages:
                if msg.get("role") in ("HumanMessage", "Human", "user"):
                    first_input = msg.get("content", "").lower()
                    break
            if first_input:
                break

    if not first_input:
        return failures

    # Find the final output
    final_output = None
    for event in reversed(events):
        if event.event_type == "final_decision":
            final_output = str(event.output_data.get("response", "")).lower()
            break

    if not final_output:
        return failures

    # Extract product/entity names from input and check if they appear in output
    # Simple heuristic: look for quoted terms or capitalized words in input
    import re
    # Look for potential entity names (capitalized words, quoted strings)
    quoted = re.findall(r'"([^"]+)"', str(first_input))
    if not quoted:
        # Look for product-like terms
        words = first_input.split()
        # Check if a specific product mentioned in input appears in output
        for event in events:
            if event.event_type == "tool_call_end":
                result = str(event.output_data)
                if "error" in result.lower() or "not found" in result.lower():
                    # A requested item wasn't found — check if something else was delivered
                    if event.event_type == "final_decision":
                        continue
                    # Check if final output mentions a different product
                    for later in events:
                        if later.event_type == "final_decision":
                            output = str(later.output_data).lower()
                            if "success" in str(event.output_data).lower() or "purchased" in output or "completed" in output:
                                failures.append({
                                    "type": "SILENT_SUBSTITUTION",
                                    "severity": "HIGH",
                                    "description": "Agent may have substituted the requested item without explicit user approval",
                                    "evidence": {
                                        "original_request": first_input[:200],
                                        "final_output": final_output[:200],
                                    },
                                    "step": len(events),
                                })
                                return failures

    return failures


def _detect_repeated_failure(events: list[Event]) -> list[dict]:
    """Detect: agent retried the same failing action multiple times."""
    failures = []
    action_attempts = {}

    for i, event in enumerate(events):
        if event.event_type == "tool_call_start":
            action = event.action
            if action not in action_attempts:
                action_attempts[action] = {"count": 0, "errors": 0, "first_step": i + 1}
            action_attempts[action]["count"] += 1

        if event.event_type == "tool_call_end":
            result = str(event.output_data).lower()
            if "error" in result or "fail" in result or "not found" in result:
                # Find the matching tool call
                for action, info in action_attempts.items():
                    if info["count"] > info["errors"]:
                        info["errors"] += 1
                        break

        if event.event_type == "error":
            # Count general errors too
            pass

    for action, info in action_attempts.items():
        if info["errors"] >= 2:
            failures.append({
                "type": "REPEATED_FAILURE",
                "severity": "MEDIUM",
                "description": f"Tool '{action}' failed {info['errors']} out of {info['count']} attempts",
                "evidence": {
                    "tool": action,
                    "attempts": info["count"],
                    "failures": info["errors"],
                },
                "step": info["first_step"],
            })

    return failures


def _detect_retrieval_mismatch(events: list[Event]) -> list[dict]:
    """Detect: retrieved context has low similarity score or doesn't match intent."""
    failures = []

    for i, event in enumerate(events):
        if event.event_type != "context_injection":
            continue

        content = event.input_data
        score = content.get("similarity_score", content.get("score", None))

        if score is not None and isinstance(score, (int, float)) and score < 0.7:
            failures.append({
                "type": "RETRIEVAL_MISMATCH",
                "severity": "MEDIUM",
                "description": f"Retrieved context has low similarity score ({score:.2f}) — may not match query intent",
                "evidence": {
                    "source": event.action,
                    "similarity_score": score,
                    "content_preview": str(content)[:200],
                },
                "step": i + 1,
            })

    return failures


def failure_summary(all_failures: list[dict]) -> dict:
    """Aggregate failure stats across multiple sessions.

    Args:
        all_failures: Combined list of failures from multiple classify_failures() calls

    Returns:
        Dict with counts per failure type and severity breakdown
    """
    by_type = {}
    by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for f in all_failures:
        ftype = f["type"]
        severity = f.get("severity", "MEDIUM")

        if ftype not in by_type:
            by_type[ftype] = {"count": 0, "description": FAILURE_TYPES.get(ftype, ""), "severities": []}
        by_type[ftype]["count"] += 1
        by_type[ftype]["severities"].append(severity)

        if severity in by_severity:
            by_severity[severity] += 1

    return {
        "total_failures": len(all_failures),
        "by_type": by_type,
        "by_severity": by_severity,
    }
