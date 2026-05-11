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
| 2 | Strands Agents on Bedrock AgentCore Runtime, Claude via Bedrock | Complete | `phase2-strands-bedrock/` |
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
- Tests/smokes hit real APIs by design (no mocking the LLM)

**Phase 1:** LangGraph 1.x, LangChain, langchain-anthropic, LangSmith for observability, yfinance for price data, Anthropic server-side `web_search_20250305` for research.

**Phase 2:** Strands Agents SDK, AWS Bedrock (Claude Haiku 4.5 via Bedrock, `eu.anthropic.claude-haiku-4-5` cross-region inference profile in `eu-west-1`), Tavily for web search via `strands-agents-tools`. Pattern: agents-as-tools (model-driven orchestration with specialist agents wired as tools). AgentCore Runtime deployment is future work; the current implementation runs locally via AWS SSO credentials.

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
│   │   ├── (Phase 1 tutorials)
│   │   └── phase-2/                  # Phase 2 tutorials
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
├── phase2-strands-bedrock/          # Phase 2 — Strands + Bedrock
│   ├── README.md
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── env-example.txt
│   ├── verify_setup.py
│   ├── docs/observations.md         # build-period text-native findings
│   └── src/briefing_agent/
│
└── phase3-vertex-gemini/            # Phase 3 — Vertex Agent Engine (planned)
    └── ...
```

---

## Key Patterns (Phase 1 — typed state graph)

These are observations from the LangGraph implementation. See [`docs/tutorials/13-architecture.md`](./docs/tutorials/13-architecture.md) and [`docs/retrospectives/phase-1-retrospective.md`](./docs/retrospectives/phase-1-retrospective.md) for the full discussion.

- **State-first design** — define the state schema before writing nodes; nodes stay small because state absorbs inter-node communication
- **Schema-as-contract** — every LLM call uses `with_structured_output` against a TypedDict; provider-level enforcement eliminates JSON parsing problems
- **`with_structured_output` was the workhorse, agent loops the exception** — eleven of twelve nodes use simple LLM patterns
- **Bounded loops, every time** — feedback loops have explicit retry caps with safety-valve routes; no infinite loops
- **Auditors need pass-bias prompts** — without explicit "what is NOT a flagged issue" guidance, auditors over-flag
- **Two-stage analyse-then-render** — separate the analytical work (synthesise) from the rendering (draft); each stage gets its own auditor

---

## Key Patterns (Phase 2 — agents-as-tools with text-native data flow)

Observations from the Strands implementation. See [`docs/tutorials/phase-2/`](./docs/tutorials/phase-2/) STEP-01 through STEP-07 and [`docs/retrospectives/phase-2-retrospective.md`](./docs/retrospectives/phase-2-retrospective.md).

- **Prompt-first design** — write the specialist's prompt and output structure before writing its 12-line factory; behaviour lives in the prompt
- **Text-native default; hybrid only where quality forces it** — specialists return prose with section-header conventions and `VERDICT: PASS/FAIL` lines. Hybrid (`structured_output_model` per specialist) was the fallback; never needed.
- **Workflow lives in the orchestrator's prompt** — declarative goal + constraints, not imperative recipe. Validated under happy path and both retry-loop failures.
- **Retry caps enforced by prose alone** — the model counts tool-call cycles from its conversation history and stops at the named limit, with explicit narration. No programmatic safety net required.
- **Preamble drift correlates with tool-equipped specialists** — research agents (with Tavily) consistently add narrative preamble; tools-less specialists go directly to structured output. Parser logic simplifies because of it.
- **Pass-bias and editorial discipline port verbatim from Phase 1** — auditor calibration, anti-weasel framing, embedded-metric prose, targeted revision. The prompts are about Claude's reasoning, not LangGraph state plumbing, so they transfer.

The biggest cross-phase lesson: **prompt-level discipline is the portable layer; framework-level scaffolding is not.**

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
- LangGraph 1.0 (Phase 1) requires TypedDict not Pydantic for state schemas; Strands (Phase 2) uses Pydantic for structured output at the agent boundary only
- Python 3.13 + Apple Silicon caused TF/ecosystem issues in earlier ML work; Phase 1 sticks to 3.12 and that policy continues across phases
- LangSmith tracing in Phase 1 carries forward conceptually but each phase has its own observability stack. Phase 2's default streaming-to-stdout is useful for dev runs; production deployment would set `callback_handler=None` on the orchestrator.
- Phase 2 uses AWS SSO for Bedrock access; AWS credentials must be available in the default credential chain (e.g., `aws sso login` before invoking)

---

## Updating this document

This file is project-wide context, maintained at phase boundaries and updated as architecture decisions change. If you notice drift between this document and reality, fix it — stale context is worse than no context.
