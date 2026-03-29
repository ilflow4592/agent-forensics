# Failure Pattern Catalog

Agent Forensics auto-detects 6 failure patterns in agent traces. Each pattern includes severity, description, evidence, and the step in the timeline where it occurred.

## Overview

| Pattern | Severity | What It Detects |
|---------|----------|-----------------|
| [`HALLUCINATED_TOOL_OUTPUT`](#hallucinated_tool_output) | HIGH | Agent ignored a tool error |
| [`MISSING_APPROVAL`](#missing_approval) | HIGH | Critical action without guardrail |
| [`SILENT_SUBSTITUTION`](#silent_substitution) | HIGH | Output differs from request |
| [`PROMPT_DRIFT_CAUSED`](#prompt_drift_caused) | MEDIUM | Decision influenced by prompt change |
| [`REPEATED_FAILURE`](#repeated_failure) | MEDIUM | Same action failed multiple times |
| [`RETRIEVAL_MISMATCH`](#retrieval_mismatch) | MEDIUM | Low-similarity RAG context used |

---

## HALLUCINATED_TOOL_OUTPUT

**Severity:** HIGH

**What it detects:** A tool returned an error (contains "error", "fail", or "not found"), but the agent's next decision proceeded without acknowledging the failure.

**Example scenario:**

```
Tool: search_api("Galaxy S25 Ultra")
  → {"error": "Product not found"}

Agent decision: "Using the search results to compare prices"   # ← Ignores the error!
```

**Why it's dangerous:** The agent acts on data that doesn't exist, leading to hallucinated conclusions and incorrect actions.

**How to fix:**

- Add error handling in your agent's decision logic
- Check tool outputs before proceeding
- Use guardrails to validate tool results before acting on them

**Detection window:** The classifier checks the next 3 events after a tool error for a decision that doesn't mention "error", "fail", "retry", or "not found" in its reasoning.

---

## MISSING_APPROVAL

**Severity:** HIGH

**What it detects:** A critical action was taken without a preceding guardrail check. Critical actions are identified by keywords: `purchase`, `buy`, `delete`, `remove`, `send`, `transfer`, `pay`, `cancel`.

**Example scenario:**

```
Agent decision: "purchase item for $32,900"    # ← No guardrail check before this!
```

**Why it's dangerous:** High-impact actions (financial transactions, data deletion, external communications) should always have an approval checkpoint.

**How to fix:**

Add guardrail checks before critical actions:

```python
f.guardrail(
    intent="buy recommended product",
    action="purchase",
    allowed=True,
    reason="Approved by procurement policy",
)
f.decision("purchase item", ...)
```

**Detection window:** The classifier looks back 5 events for any `guardrail_pass` or `guardrail_block` event.

---

## SILENT_SUBSTITUTION

**Severity:** HIGH

**What it detects:** The agent's final output doesn't match the user's original request. Specifically, a tool returned "not found" for the requested item, but the agent delivered a different item and reported success.

**Example scenario:**

```
User: "Buy Samsung Galaxy S25 Ultra"
Tool: search("S25 Ultra") → "not found"
Agent final output: "Successfully purchased Samsung Galaxy S24 FE!"  # ← Different product!
```

**Why it's dangerous:** The user receives something they didn't ask for, with no explicit approval for the substitution.

**How to fix:**

- Always confirm substitutions with the user
- Add a guardrail check when the original item is unavailable
- Include the substitution rationale in the final output

---

## PROMPT_DRIFT_CAUSED

**Severity:** MEDIUM

**What it detects:** A decision was made immediately after a prompt drift event — the decision may have been influenced by changed instructions.

**Example scenario:**

```
System prompt changes: + "Prioritize order completion rate above 95%"
Agent decision: "Substitute with alternative product"   # ← Influenced by new KPI?
```

**Why it's dangerous:** System prompt changes can silently alter agent behavior. Decisions made right after a drift may reflect the new instructions rather than the user's intent.

**How to fix:**

- Audit system prompt changes before they take effect
- Log the reason for prompt changes
- Review decisions made immediately after drift events

**Detection window:** The classifier checks the next 5 events after a `prompt_drift` for a `decision` event.

---

## REPEATED_FAILURE

**Severity:** MEDIUM

**What it detects:** The same tool was called multiple times and failed 2 or more times, suggesting the agent retried without changing its approach.

**Example scenario:**

```
Tool: flaky_api() → {"error": "timeout"}
Tool: flaky_api() → {"error": "timeout"}
Tool: flaky_api() → {"error": "timeout"}   # ← 3 failures, same tool, same approach
```

**Why it's dangerous:** Blind retries waste time and resources. The agent should adapt its strategy after a failure.

**How to fix:**

- Implement exponential backoff
- Try alternative tools or approaches after 1-2 failures
- Set a maximum retry count

---

## RETRIEVAL_MISMATCH

**Severity:** MEDIUM

**What it detects:** A `context_injection` event has a `similarity_score` (or `score`) below 0.7, suggesting the retrieved context may not match the query intent.

**Example scenario:**

```python
f.context_injection("vector_db", content={
    "document": "laptop_reviews.md",
    "similarity_score": 0.52,          # ← Below 0.7 threshold
})
```

**Why it's dangerous:** Low-relevance context can lead the agent to make decisions based on irrelevant information.

**How to fix:**

- Increase your similarity threshold in the RAG pipeline
- Use re-ranking to improve retrieval quality
- Add a "no relevant context found" fallback

**Threshold:** Score must be below 0.7 to trigger. Exactly 0.7 does not trigger.

---

## Using Failure Detection

### Single Session

```python
f = Forensics(session="my-session")
# ... agent runs ...

failures = f.classify()
for fail in failures:
    print(f"[{fail['severity']}] {fail['type']}")
    print(f"  Step {fail['step']}: {fail['description']}")
    if fail.get('evidence'):
        for key, val in fail['evidence'].items():
            print(f"  {key}: {val}")
```

### Across Sessions

```python
stats = f.failure_stats()
print(f"Total: {stats['total_failures']}")
print(f"HIGH: {stats['by_severity']['HIGH']}")

for ftype, info in stats['by_type'].items():
    print(f"{ftype}: {info['count']}x — {info['description']}")
```

### In Reports

Failures are automatically included in the forensic report under the "Failure Classification" section, with a summary table and detailed evidence for each pattern.
