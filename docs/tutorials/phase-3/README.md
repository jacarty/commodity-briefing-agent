# Tutorial — Phase 3: Google ADK on Vertex AI Agent Engine

Personal step-by-step notes from building Phase 3 of the commodity
briefing agent. Not reference documentation — these are my notes-to-self,
written chronologically as I worked through each step in coaching mode
with Claude.

Phase 3 builds the same agent as Phases 1 and 2, this time on Google's
Agent Development Kit (ADK) with Gemini 2.5 Flash, deployed to Vertex AI
Agent Engine. The orchestrator is a custom `BaseAgent` subclass that
coordinates a `ParallelAgent` (concurrent research) and two `LoopAgent`s
(audit retry loops).

For Phase 1 (LangGraph + Anthropic direct), see [`../phase-1/`](../phase-1/).
For Phase 2 (Strands + Bedrock), see [`../phase-2/`](../phase-2/).
For project-wide context, see the [top-level README](../../../README.md).
For the Phase 3 retrospective and Phase 2 vs Phase 3 comparison, see
[`../../retrospectives/phase-3-retrospective.md`](../../retrospectives/phase-3-retrospective.md).

## Index

- [STEP-01 — Orientation](./01-orientation.md)
- [STEP-02 — Environment setup](./02-environment-setup.md)
- [STEP-03 — Design](./03-design.md)
- [STEP-04 — News research](./04-news-research.md)
- [STEP-05 — Parallel specialists](./05-parallel-specialists.md)
- [STEP-06 — The synthesis layer](./06-synthesis-layer.md)
- [STEP-07 — Draft](./07-draft.md)
- [STEP-08 — Final brief](./08-final-brief.md)
- [STEP-09 — Agent Engine deployment](./09-deployment.md)
