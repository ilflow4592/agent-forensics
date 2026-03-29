# EU AI Act Compliance

The EU AI Act enters enforcement for high-risk AI systems on **August 2, 2026**. Agent Forensics helps meet the traceability and human oversight requirements.

## Relevant Requirements

### Article 14 — Human Oversight

High-risk AI systems must be designed to allow human oversight, including:

| Requirement | Article | How Agent Forensics Helps |
|-------------|---------|---------------------------|
| Understand system capabilities and limitations | 14(4)(a) | Forensic reports show every decision, tool call, and failure |
| Monitor operation and detect anomalies | 14(4)(b) | Auto-classification of 6 failure patterns with severity |
| Interpret outputs correctly | 14(4)(c) | Decision chain shows reasoning behind each output |
| Decide not to use or override | 14(4)(d) | Guardrail checkpoints record allow/block decisions |
| Intervene or interrupt | 14(4)(e) | Real-time prompt drift detection flags instruction changes |

### Article 12 — Record-Keeping

High-risk AI systems must have logging capabilities that:

| Requirement | How Agent Forensics Helps |
|-------------|---------------------------|
| Record events during operation | Every decision, tool call, error, and LLM interaction is stored |
| Identify risks and modifications | Failure classification flags risky patterns automatically |
| Enable post-market monitoring | Session-based storage allows historical analysis |
| Ensure traceability | Immutable SQLite event log with timestamps and session isolation |

### Article 9 — Risk Management

| Requirement | How Agent Forensics Helps |
|-------------|---------------------------|
| Identify and analyze known risks | Failure pattern detection across sessions |
| Estimate and evaluate residual risks | Severity classification (HIGH/MEDIUM/LOW) |
| Adopt risk management measures | Guardrail checkpoints enforce action approval |

## What Gets Recorded

Every forensic report includes:

1. **Complete Timeline** — chronological record of all agent actions with timestamps
2. **Decision Chain** — each decision point with input data and reasoning
3. **Incident Analysis** — errors, failed tools, and root cause chain
4. **Failure Classification** — auto-detected patterns with evidence
5. **Prompt Drift Analysis** — when and how instructions changed
6. **Context Injections** — which external data influenced decisions
7. **Guardrail Checkpoints** — which actions were approved or blocked
8. **Compliance Notes** — summary statistics for auditing

## Compliance Workflow

### 1. Instrument Your Agent

```python
from agent_forensics import Forensics

f = Forensics(session="prod-session-001", agent="customer-service-agent")

# Use framework integration or manual API
agent.invoke({"input": "..."}, config={"callbacks": [f.langchain()]})
```

### 2. Add Guardrails for Critical Actions

```python
f.guardrail(
    intent="refund customer order",
    action="process_refund",
    allowed=True,
    reason="Refund amount within auto-approval limit ($100)",
)
```

### 3. Track Context Sources

```python
f.context_injection(
    source="customer_db",
    content={"customer_id": "C-123", "order_history": "..."},
    reasoning="Retrieved customer context for personalized response",
)
```

### 4. Generate Compliance Reports

```python
# Per-session report
f.save_markdown("./compliance-reports")
f.save_pdf("./compliance-reports")

# Cross-session failure analysis
stats = f.failure_stats()
print(f"Total failures across all sessions: {stats['total_failures']}")
print(f"HIGH severity: {stats['by_severity']['HIGH']}")
```

### 5. Review and Audit

- Store reports alongside your system documentation
- Use `failure_stats()` for periodic risk assessments
- Review `prompt_drift` events for unauthorized instruction changes
- Audit `guardrail_block` events to verify safety mechanisms work

## Report Example

Each report ends with a compliance section:

```
## Compliance Notes

- This report supports EU AI Act Article 14 (Human Oversight) requirements.
- All agent decision points have been recorded.
- Total events captured: 15
- Decision points: 4
- Errors/incidents: 1
- Prompt drifts: 1
- Context injections: 2
- Guardrail checks: 1 passed, 0 blocked
```

## Key Dates

| Date | Event |
|------|-------|
| Aug 1, 2024 | EU AI Act entered into force |
| Feb 2, 2025 | Prohibited practices provisions apply |
| Aug 2, 2025 | General-purpose AI model obligations apply |
| **Aug 2, 2026** | **High-risk AI system requirements apply** |

## Limitations

Agent Forensics provides **traceability infrastructure** — it records what happened and why. It does not:

- Determine whether your system qualifies as high-risk (consult legal counsel)
- Provide legal certification or compliance attestation
- Replace a risk management system (but it feeds into one)
- Monitor in real-time (it analyzes after the fact)

For legal guidance on EU AI Act classification, consult qualified legal professionals familiar with your specific use case and jurisdiction.
