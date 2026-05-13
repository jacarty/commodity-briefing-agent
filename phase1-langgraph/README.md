# Phase 1 — LangGraph + Anthropic API direct

The first implementation of the Commodity Briefing Agent. Built with LangGraph's `StateGraph`, calling Claude directly via the Anthropic API.

This is one of three implementations — see the [project README](../README.md) for the broader context.

## Architecture summary

12 nodes, two bounded feedback loops, schemas typed throughout, ~35 tests against real APIs.

```
START → Plan → [4 parallel: price/news/catalysts/geopolitics] → Synthesise →
Cross-check → (pass) Draft → Sense-check → (pass) Deliver → END
                (fail) Re-research → Synthesise (loop)
                                     Sense-check (fail) → Revise → Sense-check (loop)
```

Full architecture write-up: [`../docs/tutorials/phase-1/13-architecture.md`](../docs/tutorials/phase-1/13-architecture.md).

## Setup

```bash
cd phase1-langgraph
uv sync
```

Set up the environment file (not checked in):

```bash
cp .env.example .env  # if an example exists; otherwise create .env
# Add ANTHROPIC_API_KEY=sk-ant-...
```

## Running tests

```bash
uv run pytest
```

Tests hit real APIs (Anthropic, yfinance) by design — see [`../docs/retrospectives/phase-1-retrospective.md`](../docs/retrospectives/phase-1-retrospective.md) for the rationale. Cost per full run is single-digit cents; runtime is ~3 minutes.

## Running the agent

```bash
uv run python -m briefing_agent.main
```

Produces an end-to-end commodity briefing for the configured target date. Output is the email-shaped final brief (subject, HTML body, plain-text body).

## Project layout

```
phase1-langgraph/
├── pyproject.toml
├── uv.lock
├── src/
│   └── briefing_agent/
│       ├── __init__.py
│       ├── main.py             # entry point
│       ├── graph.py            # StateGraph wiring
│       ├── nodes.py            # all node functions
│       ├── state.py            # TypedDict State definition
│       └── prompts/            # markdown prompt files
│           ├── __init__.py     # load_prompt helper
│           ├── plan.md
│           └── ...
└── tests/
    └── test_*.py
```

## Tutorial steps

The full coaching-mode walkthrough is in [`../docs/tutorials/phase-1/`](../docs/tutorials/phase-1/), STEP-01 through STEP-13.
