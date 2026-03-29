# Contributing to Agent Forensics

Thank you for your interest in contributing! This guide will help you get set up.

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Clone and Install

```bash
git clone https://github.com/ilflow4592/agent-forensics.git
cd agent-forensics

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Optional: install all framework integrations
pip install -e ".[all]"
```

### Verify Setup

```bash
python -m pytest tests/ -v
```

All 86+ tests should pass.

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=agent_forensics --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_store.py

# Run a specific test
python -m pytest tests/test_classifier.py::TestMissingApproval::test_detects_purchase_without_guardrail
```

### Test Structure

| File | What It Tests |
|------|---------------|
| `tests/test_store.py` | Event save/retrieve, session isolation, thread safety |
| `tests/test_core.py` | All Forensics methods (decision, tool_call, guardrail, etc.) |
| `tests/test_classifier.py` | Each of the 6 failure patterns |
| `tests/test_report.py` | Report generation with all event types |

## Making Changes

### Branch Naming

- `feat/description` — new features
- `fix/description` — bug fixes
- `docs/description` — documentation changes

### Code Style

- Follow existing code patterns
- No external dependencies for core functionality (framework integrations are optional)
- Use type hints for public API methods
- Tests are required for new features

### Commit Messages

Use clear, descriptive commit messages:

```
Add guardrail checkpoint recording

Support for intent vs action tracking with allow/block decisions.
Blocked actions trigger incident detection in reports.
```

## Pull Request Guidelines

1. **Create a branch** from `main`
2. **Write tests** for any new functionality
3. **Run the full test suite** and ensure all tests pass
4. **Update documentation** if you changed the public API
5. **Open a PR** with a clear description of what and why

### PR Template

```markdown
## Summary
What changed and why.

## Test Plan
How to verify the change works.
```

## Project Structure

```
agent_forensics/
├── __init__.py          # Package exports
├── core.py              # Forensics main class
├── store.py             # Event storage (SQLite)
├── classifier.py        # Failure pattern detection
├── report.py            # Report generation (Markdown + PDF)
├── dashboard.py         # Web dashboard
└── integrations/
    ├── langchain.py     # LangChain callback handler
    ├── openai_agents.py # OpenAI Agents SDK hooks
    └── crewai.py        # CrewAI callbacks

tests/
├── conftest.py          # Shared fixtures
├── test_store.py
├── test_core.py
├── test_classifier.py
└── test_report.py

docs/                    # MkDocs documentation site
```

## Questions?

Open an issue on [GitHub](https://github.com/ilflow4592/agent-forensics/issues).
