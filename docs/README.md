# Documentation

Docs hub for the Commodity Briefing Agent project. The repo builds the same conceptual agent three ways across three platforms; the documentation is organised by content type, not by phase.

For the top-level project description, see the [project README](../README.md).
For Claude Code session context, see [`../CLAUDE.md`](../CLAUDE.md).

## Tutorials

Step-by-step coaching-mode build notes, one folder per phase. These are personal notes-to-self, written chronologically as each phase was built. Not reference documentation.

- [`tutorials/phase-1/`](./tutorials/phase-1/) — LangGraph + Anthropic API direct (STEP-01 through STEP-13)
- [`tutorials/phase-2/`](./tutorials/phase-2/) — Strands Agents on Bedrock (STEP-01 through STEP-07)
- [`tutorials/phase-3/`](./tutorials/phase-3/) — Google ADK on Vertex AI Agent Engine (STEP-01 through STEP-09)

## Retrospectives

Phase-end retrospectives. Each captures what was built, what worked, what surprised, and what carries forward.

- [`retrospectives/phase-1-retrospective.md`](./retrospectives/phase-1-retrospective.md) — LangGraph
- [`retrospectives/phase-2-retrospective.md`](./retrospectives/phase-2-retrospective.md) — Strands / Bedrock (incl. Phase 1 vs Phase 2 comparison)
- [`retrospectives/phase-3-retrospective.md`](./retrospectives/phase-3-retrospective.md) — ADK / Vertex (incl. Phase 2 vs Phase 3 comparison)

A cross-phase comparison (1 vs 2 vs 3) is on the horizon as a separate piece of work.

## Decisions

Architecture Decision Records. Significant technical decisions taken during implementation that aren't already covered in tutorial steps.

- [`decisions/0001-single-reresearch-path.md`](./decisions/0001-single-reresearch-path.md)

## Process

- [`process.md`](./process.md) — development process, branch/PR cadence, pre-commit and pre-PR agent gates, trivial-change fast path

## Phase-local docs

Some build-period notes live inside the phase directories rather than under `docs/`. They cover findings specific to that phase's framework and don't generalise to the whole project.

- [`../phase2-strands-bedrock/docs/observations.md`](../phase2-strands-bedrock/docs/observations.md) — text-native findings during Phase 2 build
- [`../phase3-vertex-gemini/docs/observations.md`](../phase3-vertex-gemini/docs/observations.md) — ADK findings during Phase 3 build
