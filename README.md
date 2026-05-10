# Commodity Briefing Agent

This repo is to support initial exploration and learning of Langchain's product set (LangGraph, LangChain and LangSmith). It is a side-project to continue my wider learning around ML/GenAI, other repos cover Python, Vertex, ML, additional Agentic Flows, as well as web apps across various Cloud platforms.

The ultimate goal is to build a Daily Commodity Research agent - given the scale of public data available, Oil will be the focus to keep that side simple to source. The same agent will be created three ways:
   1. Direct on the Claude API
   2. Bedrock and AgentCore (with Claude)
   3. Vertex with Agent Engine (with Gemini)

I picked Commodities trading as it's a side interest of mine, which is why this domain rather than something more obvious like a coding assistant.
This is to deepen my hands-on experience with Bedrock/Vertex and provide comparative outcomes for the three approaches.

## Phases
Currently starting phase 2 - Bedrock and AgentCore

## Documentation

- [`docs/tutorials/`](./docs/tutorials/) — step-by-step tutorial notes (currently Phase 1; Phase 2 tutorials added as that work progresses)
- [`docs/retrospectives/`](./docs/retrospectives/) — phase retrospectives
- [`docs/decisions/`](./docs/decisions/) — architecture decision records
- [`docs/process.md`](./docs/process.md) — development process and PR cadence
- [`CLAUDE.md`](./CLAUDE.md) — project context for Claude Code sessions

## Running a phase

Each phase is independent. To work on Phase 1:

```bash
cd phase1-langgraph
uv sync
uv run pytest
```

Phase 2 will follow the same pattern once it lands.

## Tooling

- **Python 3.12**, managed via `uv`
- **Ruff** for linting and formatting (config per-phase, in each phase's `pyproject.toml`)
- **Pre-commit** hooks at the repo root, applying to all phases
- **GitHub Actions** for CI; per-phase or matrix-based as the project grows
- Conventional Commits enforced via githooks

## License

MIT — see [LICENSE](./LICENSE).
