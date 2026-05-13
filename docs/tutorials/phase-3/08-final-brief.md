# STEP-08 — Orchestrator + FinalBrief + full pipeline

The architectural climax of Phase 3. Custom `BaseAgent`
orchestrator coordinates the full pipeline; `FinalBrief` Pydantic
schema enforces the typed output at the pipeline's boundary.

This step closes the final two STEP-03 open questions and surfaces
a real ADK gotcha around state writes from custom agents.

## What's in this PR

Five new source files:

| File | Role |
|---|---|
| `src/briefing_agent/models.py` | `FinalBrief` Pydantic BaseModel — three fields ported from Phase 2 |
| `src/briefing_agent/specialists/final_brief.py` | `LlmAgent` with `output_schema=FinalBrief`, reads `{draft}` |
| `src/briefing_agent/orchestrator.py` | `PhaseThreeOrchestrator(BaseAgent)` + `build_orchestrator()` factory |
| `src/briefing_agent/smoke_orchestrator.py` | Full end-to-end smoke test |

## The pipeline assembly

```
PhaseThreeOrchestrator (custom BaseAgent)
├── STAGE 1: research_parallel (ParallelAgent)
│       news + catalysts + geo, concurrently
├── STAGE 2: fetch_price (direct function call, no LLM)
│       writes state['price_data'] via state_delta
├── STAGE 3: synthesise (LlmAgent)
│       initial synthesis
├── STAGE 4: synthesis_loop (LoopAgent)
│       cross_check + synthesise_revise, max_iterations=2
│       escalate signal absorbed
├── STAGE 5: draft (LlmAgent)
│       initial brief
├── STAGE 6: rendering_loop (LoopAgent)
│       sense_check + revise, max_iterations=2
│       escalate signal absorbed
└── STAGE 7: final_brief (LlmAgent with output_schema=FinalBrief)
        FinalBrief dict, retries once on ValidationError
```

## The escalate-suppression mechanism

The orchestrator's `_run_async_impl` walks events from each
sub-agent and clears the escalate flag before yielding:

```python
async for event in self.synthesis_loop.run_async(ctx):
    if event.actions is not None and event.actions.escalate:
        event.actions.escalate = False
    yield event
```

By the time the orchestrator sees `escalate=True` from a loop,
the loop has already exited cleanly — the escalate signal has
served its purpose. Setting it to False before yielding means
the framework doesn't propagate the signal to terminate the
orchestrator. Pipeline continues to the next stage.

The smoke validated this: both audit loops hit `max_iterations=2`
(FAIL → revise → PASS), both eventually exited via exit_loop, the
orchestrator continued past each one to the next stage.

## The state_delta bug and fix

**This is the lesson of PR 5.**

The first version of the orchestrator wrote `state["price_data"]`
via direct assignment:

```python
ctx.session.state["price_data"] = str(price_data)  # FIRST VERSION (incorrect)
yield Event(author=self.name, content=...)  # no state_delta
```

The smoke ran end-to-end. Synthesise correctly consumed the price
data via `{price_data}` template substitution. Final brief was
produced with grounded price content. **But the state summary at
the end showed `price_data: (missing)`.** The key wasn't persisted
into the canonical session state.

Root cause: in ADK, state mutations from custom BaseAgent
subclasses are persisted via `EventActions.state_delta`. Direct
assignment to `ctx.session.state[key]` writes the value into the
in-memory state dict that downstream agents in the same
invocation see — but the SessionService applies state_delta from
event actions when persisting the session. Without state_delta,
the direct assignment doesn't end up in the canonical state view.

Fix:

```python
price_data_str = str(price_data)
yield Event(
    author=self.name,
    invocation_id=ctx.invocation_id,
    content=types.Content(...),
    actions=EventActions(state_delta={"price_data": price_data_str}),
)
# Belt-and-braces: also direct-assign so downstream agents see
# the value immediately without waiting for the delta to apply
ctx.session.state["price_data"] = price_data_str
```

After the fix, the smoke shows `price_data` populated with the
full str-serialised dict at the end of the run.

**Implication for future custom BaseAgents:** state mutations
should flow through `EventActions(state_delta={...})`. Direct
assignment alone is insufficient for persistence. The belt-and-
braces approach (state_delta + direct assignment) gives both
immediate downstream visibility AND persistence into the final
session.

## The FinalBrief retry pattern

`output_schema=FinalBrief` is enforced by ADK using Pydantic's
`model_validate_json`. If the model produces invalid JSON, ADK
raises `pydantic.ValidationError`. There's no built-in retry.
Our retry catches the first error and re-runs once:

```python
try:
    async for event in self.final_brief.run_async(ctx):
        yield event
except ValidationError as first_error:
    yield Event(...)  # log the failure
    async for event in self.final_brief.run_async(ctx):
        yield event  # second attempt
```

**The retry didn't fire on either smoke run.** Both fixed and
broken runs produced valid `FinalBrief` JSON on the first
attempt. The retry path is reserved for future runs where the
model produces invalid output; it's there as defence-in-depth,
not because we observed validation failures.

## State design through the full pipeline

State keys, in the order they're populated:

| Key | Written by | Type | Final state? |
|---|---|---|---|
| `news_research` | research_parallel sub-agent | str | ✅ |
| `catalysts_research` | research_parallel sub-agent | str | ✅ |
| `geo_research` | research_parallel sub-agent | str | ✅ |
| `price_data` | orchestrator (state_delta) | str | ✅ |
| `synthesis` | synthesise → synthesise_revise | str | ✅ (overwritten) |
| `cross_check_result` | cross_check | str | ⚠️ See note |
| `draft` | draft → revise | str | ✅ (overwritten) |
| `sense_check_result` | sense_check | str | ⚠️ See note |
| `final_brief` | final_brief | dict | ✅ |

**Note on auditor state keys:** PR 3 documented the
empty-state-on-PASS pattern — when Gemini calls `exit_loop` on
PASS, its response is the function call only, leaving the state
key empty. PR 5's smoke surfaced an additional wrinkle: when
synthesis_loop hits iteration 2 (FAIL → revise → PASS), the
final cross_check_result state can be non-empty if the iteration
2 cross_check reasons about the state from iteration 1's FAIL.
In one run we saw `cross_check_result` = *"The synthesis provided
has already been audited and passed. No further action is
required."* — not the standard verdict-line format. Worth noting
that auditor state on multi-iteration runs is unreliable; the
function_call event detection is the canonical PASS signal.

## What ran

The smoke completed end-to-end in **129 seconds** after the
state_delta fix. Validation:

| Check | Result |
|---|---|
| Pipeline completed without exception | ✅ |
| Total wall-clock under 200s | ✅ (129.0s) |
| All expected state keys populated | ✅ |
| `final_brief` is a dict | ✅ |
| `final_brief` has all required fields | ✅ (subject, html_body, plain_text_body) |
| At least one exit_loop call | ✅ (2 calls — one per audit loop) |

Per-agent event counts:

| Agent | Events |
|---|---|
| research_news | 1 |
| research_catalysts | 1 |
| research_geo | 1 |
| phase_three_orchestrator | 1 (the synthetic price_data fetched event) |
| synthesise | 1 |
| cross_check | 4 (across 2 iterations) |
| synthesise_revise | 2 (1 invocation, 2 events) |
| draft | 1 |
| sense_check | 4 (across 2 iterations) |
| revise | 2 (1 invocation, 2 events) |
| final_brief | 1 |

**Both audit loops hit iteration 2.** synthesis_loop FAILed on
iteration 1, ran synthesise_revise, PASSed on iteration 2.
rendering_loop did the same. This is consistent with PR 4's
"auditors lean strict on real input" finding — but it now
appears even cross_check (the synthesis auditor, previously
more lenient than sense_check) hit FAIL on iteration 1. Model
variance is real; the loop design absorbs it.

**Total exit_loop calls: 2** — one per audit loop, on the
PASSing iteration 2 cross_check and sense_check respectively.

## STEP-03 open questions — final scoreboard

After PR 5, the scoreboard:

| Question | Answer |
|---|---|
| Prompt-port-verbatim for Gemini | ✅ Six of seven prompts ported verbatim (orchestrator is code) |
| `google_search` quality vs Tavily | ✅ Validated PR 1 |
| `ParallelAgent` parallelises | ✅ Validated PR 2 |
| `exit_loop` reliability | ✅ Validated PR 3 |
| Gemini's PASS-with-notes calibration | ⚠️ Holds for cross_check on toy inputs; on real-pipeline inputs both auditors lean strict and hit iteration 2 |
| `event.actions.escalate = False` suppression | ✅ Validated PR 5 — pipeline continued past both loops cleanly |
| `output_schema=FinalBrief` reliability | ✅ Validated PR 5 — produced valid FinalBrief on first try in both runs |

Plus PR 4's finding: revise is not surgical (full re-renders).
Plus PR 5's finding: state writes from custom agents must use
state_delta.

## Latency budget — revised

STEP-07's estimate was 90-180s. Actual: 129s on the successful
run (and 365s on the broken run before the fix, which had
3 exit_loop calls — possibly because the bug caused extra
auditor confusion, but more likely just model variance).

Revised budget for PR 6 deploy planning:

| Scenario | Time |
|---|---|
| Both audit loops PASS first try | ~70-90s |
| One audit loop FAILs once (typical) | ~120-150s |
| Both audit loops FAIL once (observed) | ~150-200s |
| Variance / outlier runs | up to ~350s |

For deploy: expect typical runs around 130-180s, plan for
outliers up to ~400s.

## A small finding worth flagging

The plain-text body of the final brief in one run had a typo —
*"This, coupled with an with an increase..."* — duplicated
phrase. This is a generation artefact at the final_brief
assembly step (the model produces JSON containing the duplicated
phrase). Not a structural failure; just noise from the model.

If we wanted to harden this, a post-validate pass over
`plain_text_body` for common duplications would catch it.
Deferred — single-run noise, not a pattern.

## What's NOT in this PR

- Agent Engine deployment — PR 6
- Phase 3 retrospective with cross-phase comparison — comes after deploy

## Reproducibility

```bash
cd phase3-vertex-gemini
uv sync   # no new deps
uv run python -m briefing_agent.smoke_orchestrator
```

Expected duration: 120-200 seconds typically, possibly longer
on outlier runs. The smoke prints per-stage events, state
summary, the final FinalBrief, and validation checks.
