# Changelog

All notable changes to Agent Forensics are documented here.

## [0.3.2] — 2026-03-29

### Added
- **Multi-Agent Support**
  - `handoff()` — record agent-to-agent delegation with context
  - `agent_stats()` — per-agent event/failure breakdown and handoff chain
  - Report: Multi-Agent Analysis section (handoff flow + per-agent breakdown)
  - Dashboard: handoff flow visualization, per-agent stat cards
- **Advanced Classification**
  - `add_pattern(fn)` — register custom failure pattern detectors
  - `classify(min_severity=)` — filter results by severity threshold
  - `on_failure(callback, webhook=)` — alert on failure detection
  - Webhook support (HTTP POST to Slack/Discord/custom endpoints)
  - `failure_stats()` includes custom patterns

## [0.3.1] — 2026-03-29

### Added
- **Dashboard V2**
  - Failure classification summary with severity badges (HIGH/MEDIUM/LOW)
  - Guardrail pass/block visualization cards
  - Event search & filter (by type dropdown + keyword search)
  - Session diff tab (side-by-side comparison with divergence highlighting)
  - CSV export button
  - New API endpoints: `/api/diff`, `/api/export`
  - Support for all event types (context_injection, prompt_drift, guardrails)

## [0.3.0] — 2026-03-29

### Added
- **Failure auto-classification** — 6 rule-based failure patterns detected automatically
  - `HALLUCINATED_TOOL_OUTPUT` — agent ignored tool errors
  - `MISSING_APPROVAL` — critical action without guardrail
  - `SILENT_SUBSTITUTION` — output differs from user request
  - `PROMPT_DRIFT_CAUSED` — decision influenced by prompt change
  - `REPEATED_FAILURE` — same tool failed multiple times
  - `RETRIEVAL_MISMATCH` — low-similarity RAG context used
- `classify()` — auto-classify failures in a session trace
- `failure_stats()` — aggregate failure patterns across sessions
- `failure_summary()` — count failures by type and severity
- Failure classification section in forensic reports
- pytest test suite (86 tests) with GitHub Actions CI (Python 3.10/3.11/3.12)
- Live demo: "The Silent $47K Mistake" (`demo.py`)
- README badges (CI, PyPI, License)
- MkDocs documentation site

## [0.2.2] — 2026-03-28

### Added
- **Deterministic replay support**
  - `get_replay_config()` — extract model config + step sequence from a session
  - `replay_diff()` — compare original vs replayed sessions
- `llm_call()` — record LLM calls with model config (model, temperature, seed)

## [0.2.1] — 2026-03-28

### Added
- **Guardrail checkpoints**
  - `guardrail()` — record allow/block decisions for critical actions
  - `guardrail_pass` / `guardrail_block` event types
  - Blocked actions appear in causal chain as `[GUARDRAIL BLOCKED]`
  - Guardrail stats in compliance notes section

## [0.2.0] — 2026-03-27

### Added
- **Context injection tracking**
  - `context_injection()` — record RAG chunks, memory, retrieved docs
  - Context injection section in reports
- **Prompt drift detection**
  - `prompt_state()` — record system prompt with auto-diff
  - Automatic drift detection when prompt changes between calls
  - Prompt drift analysis section in reports

## [0.1.0] — 2026-03-26

### Added
- Initial release
- Core recording API: `decision()`, `tool_call()`, `error()`, `finish()`
- SQLite-backed event store with session isolation
- Forensic report generation (Markdown + PDF)
- Timeline, decision chain, incident analysis, causal chain
- Web dashboard with dark theme
- Framework integrations: LangChain, OpenAI Agents SDK, CrewAI
- EU AI Act Article 14 compliance notes
- PyPI package: `pip install agent-forensics`
