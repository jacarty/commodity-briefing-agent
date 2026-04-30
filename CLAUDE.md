# LangChain Exploration — Claude Code Context

## Project Overview

This repo is to support initial exploration and learning of Langchain's product set (LangGraph, LangChain and LangSmith). Built collaboratively in coaching mode: I (the human) write code, Claude provides explanations and reviews. See docs/tutorial/ once it exists.

The ultimate goal is to build a Daily Commodity Research agent - given the scale of data available Oil will be the focus to keep that side simple. The same agent will be created three ways across Anthropic, Bedrock and Vertex for comparison.

**Build Guide:** `TBD`
**Process:** `docs/process.md` — branch/PR cadence, pre-commit + pre-PR agent gates, trivial-change fast path, phase-boundary rituals. Read this before any feature work.

---

## Architecture

<!-- High-level architecture diagram or description -->



<!-- Key technology choices -->
Tech Stack:
- **Python: 3.12**
- **uv**
- **LangChain/LangGraph 1.0**
- **CI/CD: GitHub Actions**
- **Tavily for non-native search in phases 2 and 3**
Phases:
- **Phase 1 - Claude API**
- **Phase 2 - Bedrock and AgentCore**
- **Phase 3 - Vertex and Agent Engine**

<!-- Environment details -->

<!-- Example:
**TBD
-->

---

## Repository Structure

```
project/
├── CLAUDE.md                        # This file
├── docs/
│   ├── build-guides/                # Implementation guides when created
│   ├── process.md                   # Development process and agent cadence
│   └── decisions/                   # Architecture Decision Records
├── ...                              # Project-specific structure
```

<!-- Document your project's directory structure here.
     Keep this updated — the doc-generator agent refreshes it at phase boundaries. -->

---

## Key Patterns

TBD - will populate in Phase 1

---


## Git Workflow

**Branch strategy:** Phase branches → PR → merge to main.

```
main                    ← production; protected
└── feature/<slug>      ← feature work
└── fix/<slug>          ← bug fixes
```

<!-- Document your branch naming conventions and typical flow -->

---

## Deployment

TBD - will populate in Phase 1

---

## Common Pitfalls & Constraints

uv is new to me — first project using it instead of pip/venv
LangGraph 1.0 state schemas must be TypedDict not Pydantic
Experienced Python 3.13 / Vertex ecosystem issues with ML prior
Phase 1's LangSmith setup carries forward to Phases 2 and 3 unchanged — observability is the constant; the rest swaps

---

## Updating this document

This file is maintained by the **doc-generator** agent at phase boundaries and should reflect the current state of the codebase. If you notice drift between this document and reality, fix it — stale context is worse than no context.
