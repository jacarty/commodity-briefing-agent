# Tutorial — Phase 2: Strands Agents on Bedrock AgentCore

Personal step-by-step notes from building Phase 2 of the commodity
briefing agent. Not reference documentation — these are my notes-to-self,
written chronologically as I worked through each step in coaching mode
with Claude.

Phase 2 builds the same agent as Phase 1, but on Strands Agents with the
agents-as-tools pattern, hosted on Bedrock AgentCore Runtime, with Claude
via Bedrock instead of the Anthropic API direct.

For Phase 1 (LangGraph + Anthropic direct), see [`../phase-1/`](../phase-1/).
For project-wide context, see the [top-level README](../../../README.md).
For the Phase 2 retrospective and Phase 1 vs Phase 2 comparison, see
[`../../retrospectives/phase-2-retrospective.md`](../../retrospectives/phase-2-retrospective.md).

## Index

- [STEP-01 — Orientation](./01-orientation.md)
- [STEP-02 — Environment setup](./02-environment-setup.md)
- [STEP-03 — Design](./03-design.md)
- [STEP-04 — Research data sources](./04-research-data-sources.md)
- [STEP-05 — The synthesis layer](./05-synthesis-layer.md)
- [STEP-06 — The rendering layer](./06-rendering-layer.md)
- [STEP-07 — The orchestrator](./07-orchestrator.md)
