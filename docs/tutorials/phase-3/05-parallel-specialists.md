# STEP-05 — Parallel research: catalysts + geo + ParallelAgent

The full research layer lands. Adds two more specialists
(`research_catalysts`, `research_geo`), introduces the `workflows/`
subpackage for ADK workflow agents, and wraps the three research
streams in a `ParallelAgent` for concurrent execution.

This step validates a major STEP-03 design assumption: that
`ParallelAgent` actually parallelises. It does — three concurrent
research streams complete in roughly the time of one.

It also surfaces one real prompt-engineering finding for the
eventual orchestrator (PR 5).

## What's in this PR

Two prompts, two specialists, one workflow agent, three smoke tests:

| File | Role |
|---|---|
| `src/briefing_agent/prompts/catalysts.md` | Catalysts prompt, ports verbatim from Phase 2 |
| `src/briefing_agent/prompts/geopolitics.md` | Geopolitics prompt, ports verbatim from Phase 2 |
| `src/briefing_agent/specialists/research_catalysts.py` | Catalysts `LlmAgent` factory |
| `src/briefing_agent/specialists/research_geo.py` | Geopolitics `LlmAgent` factory |
| `src/briefing_agent/workflows/__init__.py` | Empty package marker — new subpackage |
| `src/briefing_agent/workflows/research_parallel.py` | `ParallelAgent` wrapping the three specialists |
| `src/briefing_agent/smoke_research_catalysts.py` | Per-specialist smoke |
| `src/briefing_agent/smoke_research_geo.py` | Per-specialist smoke |
| `src/briefing_agent/smoke_research_parallel.py` | Workflow smoke with state inspection |

## What ports verbatim from Phase 2

Both prompts (`catalysts.md`, `geopolitics.md`) — character-for-
character identical to Phase 2's. The prompt-port-verbatim
hypothesis (validated for `news` in PR 1) holds for both.

The two new specialists follow the `research_news.py` shape almost
mechanically — only the name, description, prompt file, and
`output_key` differ.

## The new piece: workflow agents

Phase 1 used LangGraph's `StateGraph` for workflow control. Phase
2 had no workflow primitives — orchestration was prose-driven via
the orchestrator's prompt. Phase 3 introduces ADK's workflow
agents as a third subpackage:

```
src/briefing_agent/
├── prompts/        # markdown + loader
├── specialists/    # LlmAgent factories (one per role)
├── tools.py        # fetch_price (no decorator)
├── runner.py       # async smoke-test helper
└── workflows/      # NEW — ADK workflow agents (ParallelAgent here, LoopAgents later)
```

`workflows/research_parallel.py` builds a `ParallelAgent` containing
the three research specialists. Each sub-agent runs in its own
InvocationContext branch with shared `session.state` access.
Outputs land at distinct keys — `news_research`,
`catalysts_research`, `geo_research` — so there are no race
conditions.

The orchestrator (PR 5) will invoke this `ParallelAgent` directly
as the first stage of the pipeline.

## What ran

Three smoke tests, all passed.

### `smoke_research_catalysts`

Seven EVENT blocks, all six required fields per event. Real
events for the target date — US CPI, API crude stock, ADNOC Gas
earnings, Petrobras earnings, FOMC Williams + Goolsbee speeches,
BoJ Summary of Opinions. Surprise thresholds were concrete where
possible. Format compliance was exact.

One observation: the prompt doesn't cap event count and Gemini
returned 7. The last 2-3 events (Fed speakers, BoJ summary) have
diminishing relevance to crude oil specifically — they're general
macro that *might* move crude indirectly. The catalysts prompt
may want a soft cap added in a future revision. Deferred — not
PR 2 scope.

### `smoke_research_geo`

Five THEME blocks, all five required fields. Five genuinely
distinct structural themes — no repetition, no causal overlap.
Confidence ratings all "high", well-justified.

The prompt's "distinct themes only — don't restate the same story
under different labels" instruction held. Phase 2 noted the same
discipline; carries cleanly to Gemini.

### `smoke_research_parallel` — the validation run

```
Run complete in 18.2s (3 events total)
```

Three things to call out:

**(1) Parallel execution genuinely parallelises.**

Each individual specialist smoke took roughly 20-40 seconds.
The parallel run completed in 18.2 seconds — comparable to (or
slightly faster than) a single standalone specialist. The
latency hypothesis from STEP-03 held cleanly: three concurrent
research streams complete in roughly the time of one. This is
the free win from `ParallelAgent`.

**(2) Only 3 events in the entire stream.**

Each specialist produced exactly one event from the Runner's
perspective. Intermediate tool-call events (the `google_search`
invocations inside each specialist) did not surface to the
external event stream — they're consolidated inside each
sub-agent's run before its final response is yielded upward.

Good news for the orchestrator: PR 5 won't need to handle
interleaved tool calls from three concurrent specialists. The
parallel stage looks like three coarse "specialist finished"
notifications from the outside.

Worth noting: this means observability of *what each specialist
did internally* requires looking at each sub-agent's session
branch, not the top-level event stream. Phase 2's per-specialist
trace was richer because each specialist ran sequentially through
the orchestrator and emitted all its events upward.

**(3) Per-stream output was slightly terser than standalone.**

Comparing standalone vs parallel outputs for the same specialists:

| Stream | Standalone | Parallel |
|---|---|---|
| News | 5 items | 4 items |
| Geo | 5 themes | 4 themes |
| Catalysts | 7 events | (standalone-only this run) |

This isn't variance — it's a prompt-engineering finding. In
standalone smokes, the user message was *tailored per specialist*
("Find the most important oil-related news...", "Identify the
structural and macro geopolitical themes..."). In the parallel
smoke, the user message was generic: "Conduct full research
across news, catalysts, and geopolitics."

Each sub-agent received the generic message and produced slightly
fewer items. The system prompt (which says what each specialist
produces) still drove format and quality, but the user-message
context was thinner, and that showed in item count.

### The implication for PR 5 orchestrator design

`ParallelAgent` forwards a single message to all sub-agents.
There are three options for the orchestrator:

| Option | Description | Trade-off |
|---|---|---|
| (a) **Strengthen the prompts** | Make each specialist's system prompt self-sufficient so the user message can be minimal ("Target date: X. Commodity: crude oil.") | Editorial discipline stays in prompts (matches Phase 2's principle) |
| (b) **Sequential invocations** | Orchestrator invokes each specialist separately with tailored messages | Defeats the point of ParallelAgent — back to 3× latency |
| (c) **Pre-stage state writer** | Small "prep" step writes per-specialist instructions to session.state before the parallel stage runs | Adds complexity; specialists would need to read state for context |

**Leaning (a).** The principle "editorial discipline lives in
prompts" applies cleanly here. Each specialist's system prompt
already describes its role; in the parallel context, the user
message can degenerate to bare context (date + commodity), and
each specialist reads its system prompt to know what to do.

Will revisit in PR 5 when we wire the actual orchestrator.

## STEP-03 open questions

Three of STEP-03's six open questions have now been answered:

| Question | Status |
|---|---|
| Prompt-port-verbatim for Gemini | ✅ Validated for news (PR 1), catalysts (PR 2), geo (PR 2) |
| google_search quality vs Tavily | ✅ Content competitive; URL shape differs (PR 1 finding) |
| ParallelAgent actually parallelises | ✅ 18s for 3 streams that take ~20s individually |

Three remain:

| Question | Answered by |
|---|---|
| `exit_loop` reliability | PR 3 |
| `event.actions.escalate = False` suppression | PR 5 |
| Gemini's PASS-with-notes calibration | PR 3 |
| `output_schema=FinalBrief` reliability | PR 5 |

(That's four lines but only three open questions — `exit_loop`
and `escalate` suppression are related; they share a root cause
if either fails.)

## Findings to carry forward

| Finding | Implication for next PRs |
|---|---|
| Workflow agents work as documented | Use `SequentialAgent` / `LoopAgent` in PRs 3-4 with confidence |
| Event stream from workflow agents is coarse | Orchestrator observability (PR 5) may need per-branch session inspection rather than top-level event walking |
| Generic user message → terser output | PR 5 orchestrator should keep user messages minimal and rely on system prompts for editorial control |
| Catalysts prompt produces 7+ events | Consider a soft cap in the catalysts prompt — but deferred, may surface other issues first |
| State inspection via `session_service.get_session(...).state` works cleanly | Pattern reusable for any workflow-agent smoke |

## What's NOT in this PR

- Synthesis layer + retry loop — PR 3
- Rendering layer + retry loop — PR 4
- Custom orchestrator + `FinalBrief` — PR 5
- Agent Engine deployment — PR 6

## Reproducibility

```bash
cd phase3-vertex-gemini
uv sync
uv run python -m briefing_agent.smoke_research_catalysts
uv run python -m briefing_agent.smoke_research_geo
uv run python -m briefing_agent.smoke_research_parallel
```

Outputs vary run-to-run (LLM non-determinism). The format
compliance and the parallel-execution timing pattern are stable.
