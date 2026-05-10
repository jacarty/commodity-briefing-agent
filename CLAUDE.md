# Commodity Briefing Agent — Claude Code Context

## Project Overview

A daily commodity research agent (oil briefing) built three ways across three architectures, for comparison. Built collaboratively in coaching mode: I (the human) write the code, Claude provides explanations, reviews, and design discussion. Code-second; design-first.

The point of the project isn't shipping one agent. It's building the same conceptual agent on three platforms and learning what's portable about agent design vs what's framework-specific.

**Process:** [`docs/process.md`](./docs/process.md) — branch/PR cadence, pre-commit + pre-PR agent gates, trivial-change fast path, phase-boundary rituals. Read this before any feature work.

---

## Phases

| Phase | Architecture | Status | Path |
|---|---|---|---|
| 1 | LangGraph + Anthropic API direct | Complete | `phase1-langgraph/` |
| 2 | Strands Agents on Bedrock AgentCore Runtime, Claude via Bedrock | Starting | `phase2-strands-bedrock/` |
| 3 | Vertex AI Agent Engine, Gemini via Vertex | ⬜ Planned | `phase3-vertex-gemini/` |

Each phase is a standalone Python project with its own `pyproject.toml`, dependencies, and tests. Shared infrastructure (linter config, CI, githooks, top-level docs) lives at the root.

---

## Tech Stack

**Common:**
- Python 3.12
- `uv` for dependency management (per-phase)
- Ruff for linting/formatting
- Pre-commit hooks at the repo root
- GitHub Actions for CI
- Conventional Commits enforced via githooks
- Tests hit real APIs by design (no mocking the LLM)

**Phase 1:** LangGraph 1.x, LangChain, langchain-anthropic, LangSmith for observability, yfinance for price data, Anthropic server-side `web_search_20250305` for research.

**Phase 2:** Strands Agents SDK, AWS Bedrock (Claude via Bedrock), AgentCore Runtime for hosting, Tavily for web search (server-side `web_search_20250305` is not on Bedrock). Pattern: agents-as-tools (model-driven orchestration with specialist agents wrapped as `@tool`).

**Phase 3:** Vertex AI Agent Engine, Gemini via Vertex. Specifics TBD when Phase 3 starts.

---

## Repository Structure

```
commodity-briefing-agent/
├── CLAUDE.md                        # This file — project-wide context
├── README.md                        # Top-level project description
├── LICENSE
├── docs/                            # Cross-phase documentation
│   ├── tutorials/                   # Step-by-step tutorial notes
│   ├── retrospectives/              # Phase retrospectives
│   ├── decisions/                   # Architecture Decision Records
│   └── process.md                   # Development process
├── .github/                         # CI workflows
├── .githooks/                       # Conventional Commit hooks
├── .pre-commit-config.yaml          # Pre-commit hooks (apply to all phases)
│
├── phase1-langgraph/                # Phase 1 — LangGraph + Anthropic
│   ├── README.md
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── src/briefing_agent/
│   └── tests/
│
├── phase2-strands-bedrock/          # Phase 2 — Strands + Bedrock (incoming)
│   └── ...
│
└── phase3-vertex-gemini/            # Phase 3 — Vertex Agent Engine (planned)
    └── ...
```

---

## Key Patterns (Phase 1)

These are observations from the LangGraph implementation. Whether they generalise across architectures is what Phases 2 and 3 will test. See [`docs/tutorials/13-architecture.md`](./docs/tutorials/13-architecture.md) and [`docs/retrospectives/phase-1-retrospective.md`](./docs/retrospectives/phase-1-retrospective.md) for the full discussion.

- **State-first design** — define the state schema before writing nodes; nodes stay small because state absorbs inter-node communication
- **Schema-as-contract** — every LLM call uses `with_structured_output` against a TypedDict; provider-level enforcement eliminates JSON parsing problems
- **`with_structured_output` was the workhorse, agent loops the exception** — eleven of twelve nodes use simple LLM patterns; only one node justified `create_agent`, and even that was eventually migrated
- **Bounded loops, every time** — feedback loops have explicit retry caps with safety-valve routes; no infinite loops
- **Auditors need pass-bias prompts** — without explicit "what is NOT a flagged issue" guidance, auditors over-flag
- **Two-stage analyse-then-render** — separate the analytical work (synthesise) from the rendering (draft); each stage gets its own auditor

---

## Git Workflow

**Branch strategy:** Phase branches → PR → merge to main.

```
main                          ← production; protected
└── feature/<phase>/<slug>    ← feature work, scoped to a phase
└── fix/<slug>                ← bug fixes
└── docs/<slug>               ← docs-only changes (commit direct to main where appropriate)
```

Conventional Commits enforced via githooks. See `docs/process.md` for branch/PR cadence and the trivial-change fast path.

---

## Common Pitfalls & Constraints

- `uv` was new at project start; per-phase `pyproject.toml` and `uv.lock` mean each phase manages its own environment
- LangGraph 1.0 (Phase 1) requires TypedDict not Pydantic for state schemas; Strands (Phase 2) uses Pydantic for structured output
- Python 3.13 + Apple Silicon caused TF/ecosystem issues in earlier ML work; Phase 1 sticks to 3.12 and that policy continues
- LangSmith tracing in Phase 1 carries forward conceptually but each phase has its own observability stack (Phase 2 uses OpenTelemetry via Strands → CloudWatch)

---

## Updating this document

This file is project-wide context, maintained at phase boundaries by the **doc-generator** agent and updated as architecture decisions change. If you notice drift between this document and reality, fix it — stale context is worse than no context.
