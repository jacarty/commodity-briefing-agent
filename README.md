# Commodity Briefing Agent

This repo is to support initial exploration and learning of agent frameworks across cloud platforms. It is a side-project to continue my wider learning around ML/GenAI, other repos cover Python, Vertex, ML, additional Agentic Flows, as well as web apps across various Cloud platforms.

The ultimate goal is to build a Daily Commodity Research agent — given the scale of public data available, Oil will be the focus to keep that side simple to source. The same agent is being created three ways:
   1. LangGraph with Claude via Anthropic API direct
   2. Strands Agents on Bedrock AgentCore Runtime (Claude via Bedrock)
   3. ADK on Vertex AI Agent Engine (Gemini via Vertex)

I picked Commodities trading as it's a side interest of mine, which is why this domain rather than something more obvious like a coding assistant.
This is to deepen my hands-on experience with Bedrock/Vertex and provide comparative outcomes for the three approaches.

## Phases
- **Phase 1** (LangGraph) — complete. 12 nodes, two bounded feedback loops, ~35 tests against real APIs.
- **Phase 2** (Strands / Bedrock) — complete. 1 orchestrator + 8 specialists + 1 plain tool, agents-as-tools pattern, manual smoke tests.
- **Phase 3** (ADK / Vertex / Gemini) — complete. Custom `BaseAgent` orchestrator + `ParallelAgent` + two `LoopAgent` audit loops + 8 specialists, deployed to Vertex AI Agent Engine.

## Documentation

- [`docs/README.md`](./docs/README.md) — docs hub: index of tutorials, retrospectives, decisions
- [`docs/tutorials/`](./docs/tutorials/) — step-by-step tutorial notes, one folder per phase
- [`docs/retrospectives/`](./docs/retrospectives/) — phase retrospectives (one per phase)
- [`docs/decisions/`](./docs/decisions/) — architecture decision records
- [`docs/process.md`](./docs/process.md) — development process and PR cadence
- [`CLAUDE.md`](./CLAUDE.md) — project context for Claude Code sessions
- [`docs/retrospectives/`](./docs/retrospectives/when-this-pattern-earns-its-keep.md) — final reflections on the use-case

## Running a phase

Each phase is independent. To work on a phase:

```bash
cd phase1-langgraph   # or phase2-strands-bedrock, or phase3-vertex-gemini
uv sync
```

Then follow the phase's README for entry points and smoke/test commands.

## Tooling

- **Python 3.12**, managed via `uv`
- **Ruff** for linting and formatting (config per-phase, in each phase's `pyproject.toml`)
- **Pre-commit** hooks at the repo root, applying to all phases
- **GitHub Actions** for CI; per-phase or matrix-based as the project grows
- Conventional Commits enforced via githooks

## License

MIT — see [LICENSE](./LICENSE).
