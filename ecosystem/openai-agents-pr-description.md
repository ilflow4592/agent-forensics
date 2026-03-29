# OpenAI Agents SDK Example PR

## Target Repo
`openai/openai-agents-python` → `examples/` or `cookbook/`

## PR Title
`Add forensic reporting example with agent-forensics`

## PR Description

```markdown
## Description

Add an example demonstrating forensic reporting for OpenAI Agents using
[agent-forensics](https://github.com/ilflow4592/agent-forensics).

The example shows how to:
- Add forensic hooks to an agent with one line (`hooks=f.openai_agents()`)
- Auto-capture all decisions, tool calls, and LLM interactions
- Generate a forensic report after agent execution
- Auto-classify failure patterns (hallucinated tool output, missing approval, etc.)
- Extract model config for deterministic replay

This is useful for:
- Debugging agent failures ("why did the agent do that?")
- EU AI Act compliance (Article 14 — decision traceability)
- Comparing agent behavior across runs (replay diff)

## Usage

```bash
pip install openai-agents agent-forensics
python examples/openai_agents_forensics_example.py
```

## Dependencies

- `agent-forensics` (optional, only needed for this example)
```
