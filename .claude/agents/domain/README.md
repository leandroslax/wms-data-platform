# Domain Agents

## Active for WMS

- `wms-platform-builder`: primary domain specialist for this repository.

## Retained from the imported base

The rest of the agent library under `.claude/agents/` is intentionally kept as reusable support:

- `ai-ml/`: architecture, prompting, and LLM optimization
- `code-quality/`: implementation, cleanup, review, documentation, scripting
- `communication/`: planning and meeting analysis
- `exploration/`: codebase and KB exploration
- `domain/aide-*`: optional slide-related helpers inherited from the base library

## Rule

When working in this repository, prefer `wms-platform-builder` for domain tasks and use the other agents as supporting specialists.
