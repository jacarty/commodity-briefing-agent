# STEP-06 — Synthesis layer: cross-stream view + audit loop

The first non-research layer lands. Adds the synthesise specialist
(with initial and revise variants), the cross_check auditor with
exit_loop bound, and the `LoopAgent`-based synthesis audit loop —
the first real test of ADK's iterative-refinement primitive.

This step answers two of STEP-03's six open questions:

| Question | Answer |
|---|---|
| `exit_loop` reliability | **Held.** Loop terminated cleanly in both happy-path and fail→revise-then-PASS scenarios. The alternating-but-not-exiting behaviour from GitHub issues #2988/#2692 didn't manifest. |
| Gemini's PASS-with-notes calibration | **Excellent.** Auditor caught all six fabricated issues plus one extra, ignored minor variance, produced clean structured output. At least as good as Phase 2's Haiku. |

It also surfaces one unanticipated finding that affects PR 5's
orchestrator design (see "The empty-state-on-PASS finding" below).

## What's in this PR

Two prompts, three specialist variants, one workflow, three smokes:

| File | Role |
|---|---|
| `src/briefing_agent/prompts/synthesise.md` | Verbatim port from Phase 2 |
| `src/briefing_agent/prompts/cross_check.md` | Phase 2 port + small footer instructing exit_loop call on PASS |
| `src/briefing_agent/tools.py` | Adds `exit_loop` tool alongside `fetch_price` |
| `src/briefing_agent/specialists/synthesise.py` | `build_synthesise` (initial) and `build_synthesise_revise` (in-loop) |
| `src/briefing_agent/specialists/cross_check.py` | `build_cross_check` with `exit_loop` tool bound |
| `src/briefing_agent/workflows/synthesis_loop.py` | `LoopAgent(cross_check, synthesise_revise)`, max_iterations=2 |
| `src/briefing_agent/smoke_synthesise.py` | Live-chain smoke (research → synthesise via state) |
| `src/briefing_agent/smoke_cross_check.py` | Dual scenario (PASS via real synthesis, FAIL via fabricated bad synthesis) |
| `src/briefing_agent/smoke_synthesis_loop.py` | Dual scenario (happy path, fail→revise→pass path) |

## What ports verbatim from Phase 2

`synthesise.md` ports unchanged. `cross_check.md` ports unchanged
**except for a small footer section** ("Signalling the loop") that
instructs the model to call `exit_loop` on PASS and not call it on
FAIL. This is the minimum-necessary adaptation:

- Phase 2 routed audits by parsing the VERDICT line from the
  auditor's output text. The orchestrator's prose-driven workflow
  did the conditional branching.
- Phase 3 routes audits via function calls. The auditor calls
  `exit_loop` (which sets `tool_context.actions.escalate = True`)
  on PASS, and the parent LoopAgent reads the escalate signal to
  terminate.

Both routes preserve the same intent. The audit-methodology body
of the prompt — what to check, what not to check, the "bias toward
passing" rule, the output format — is unchanged.

## The two synthesise variants

ADK's idiomatic refinement pattern from the docs is:

```
Initial generator (outside loop)
LoopAgent:
  ├── Critic (first in loop) — reads state, decides PASS/FAIL
  └── Refiner (second in loop) — runs only on FAIL
```

We mirror this exactly. Two synthesise factory functions in the
same module:

- `build_synthesise()` — runs once before the audit loop. Reads
  the four research streams via template substitution, writes
  to `state["synthesis"]`.
- `build_synthesise_revise()` — runs inside the audit loop on
  FAIL. Reads the previous synthesis AND `cross_check_result`,
  produces a revised synthesis, overwrites `state["synthesis"]`.

Both use the same system prompt (`synthesise.md`). The difference
is the instruction wrapper — the revise variant has an "address
the audit's findings" instruction prepended. Both write to the
same `output_key="synthesis"`, using ADK's state-overwriting
pattern from the docs (initial writer + refiner share the key;
the critic always reads the latest version via `{synthesis}`).

## The cross_check loop wiring

```python
synthesis_loop = LoopAgent(
    name="synthesis_loop",
    sub_agents=[
        build_cross_check(),         # critic first
        build_synthesise_revise(),   # refiner second
    ],
    max_iterations=2,
)
```

Order matters: **cross_check runs FIRST** in each iteration. If
PASS, exit_loop is called and synthesise_revise never runs in
that iteration. If FAIL, synthesise_revise runs and writes a
revised `state["synthesis"]`, then iteration advances to the
next loop pass (cross_check runs again on the revised synthesis).

`max_iterations=2` matches Phase 2's retry budget. Phase 1 used
3; Phase 2 retrospective concluded 2 was right. Per STEP-03, the
orchestrator (PR 5) will absorb the escalate signal from this
loop's exit so it doesn't halt the parent pipeline (the
LoopAgent-escalate-propagation issue from GitHub issue #1376).

## What ran

All three smokes passed. Walking through each:

### `smoke_synthesise`

Five-section synthesis produced cleanly. All five mandatory
headers (DOMINANT NARRATIVE, PRICE INTERPRETATION, CROSS-STREAM
SIGNALS, RISKS TO VIEW, HEADLINE METRICS) present in order.
Content grounded in real research (Strait of Hormuz, SPR
release, Saudi Aramco CEO's 1bn barrel warning). 14.1 seconds
for the synthesise call.

**Quiet success worth flagging:** the synthesis correctly
consumed `{price_data}` despite being a dict serialised via
Python's `str()`. The serialised representation contains
`'last_close': 101.56, 'daily_change_pct': 3.56` — and Gemini
parsed it into "3.56% surge" and "$101" references correctly.
Template substitution + str-serialised dict works for our
needs. No JSON marshalling required.

### `smoke_cross_check`

**PASS scenario:** auditor returned VERDICT: PASS (via
function_call), called exit_loop. The cross_check_result key
in state was empty — see "The empty-state-on-PASS finding"
below for why.

**FAIL scenario** (fabricated bad synthesis):

The bad synthesis had three deliberate issues:
1. DOMINANT NARRATIVE said China demand was the lead; CROSS-
   STREAM SIGNALS said Hormuz was the lead (consistency)
2. HEADLINE METRICS included "$67.50 spot" when price_data
   showed $101.59 (grounding)
3. HEADLINE METRICS included "1.2% decline" when research said
   "rise modestly by 360k bpd" (grounding)

The auditor caught all three, plus surfaced a fourth issue I
hadn't planted (an omission of OPEC actual output context that
made a stated production increase misleadingly positive).
Format compliance perfect: VERDICT line, SUMMARY,
CONSISTENCY/CALIBRATION/GROUNDING ISSUES sections, RE-RESEARCH
TARGETS section. exit_loop correctly NOT called on FAIL.

### `smoke_synthesis_loop`

**Happy path** (real synthesis): 1 cross_check iteration, 0
synthesise_revise iterations, exit_loop called, loop exited in
13.3 seconds. Exactly the design.

**Fail→revise path** (fabricated bad synthesis):
- Iteration 1: cross_check FAILed the bad synthesis →
  synthesise_revise ran and produced a revised synthesis
- Iteration 2: cross_check PASSed the revised synthesis →
  exit_loop called → loop exited

2 cross_check events, 1 synthesise_revise event, exit_loop=True,
total 43.7 seconds. **The revise actually worked** — the revised
synthesis correctly identified Hormuz as the dominant story
(reversing the fabricated synthesis's wrong China-demand
emphasis) and produced coherent, grounded HEADLINE METRICS.

## The empty-state-on-PASS finding

This is the one unanticipated finding worth dwelling on.

**Observed:** in the PASS scenario, `state["cross_check_result"]`
is empty. The auditor called exit_loop but didn't write any
text to state.

**Root cause:** when Gemini's response is a function call, it's
*just* the function call — no text part alongside. ADK saw a
function_call-only response and the warning surfaced:

> *"there are non-text parts in the response: ['function_call'],
> returning concatenated text result from text parts."*

There are no text parts. The agent's `output_key="cross_check_result"`
captures the model's text response — which is empty. So state
ends up with no audit text.

This is consistent with the docs pattern:
> *"You must EITHER call exit_loop OR output improved essay
> text. Never do both in the same response."*

Gemini learned this constraint and applies it: on PASS it calls
the tool, on FAIL it outputs text.

**Implications for PR 5 orchestrator:**

1. **Detection of PASS must be via the function_call event**,
   not via parsing `state["cross_check_result"]`. The orchestrator
   needs to walk events and look for `part.function_call.name
   == "exit_loop"`. The state key will be empty/None after a
   PASS.

2. **No human-readable audit notes captured on PASS.** Phase 2's
   "VERDICT: PASS\n\nSUMMARY\nThe synthesis is grounded..." was
   in state. Phase 3's PASS gives us just the function call. For
   debugging/observability, we lose the "why" of the pass.

3. **Workaround if we want the PASS rationale captured:** modify
   the cross_check prompt to require text output BEFORE calling
   exit_loop. The docs example warns against "EITHER/OR", but
   models can produce both if explicitly told to. Worth trying
   in PR 4/5 if we find the empty-PASS state painful.

For now: detection-via-function-call is the right pattern. The
orchestrator design (STEP-03) already used this signal; nothing
to revise.

## STEP-03 open questions

After PR 3, the scoreboard:

| Question | Status |
|---|---|
| Prompt-port-verbatim for Gemini | ✅ Validated across all four specialists tested so far (news, catalysts, geo, synthesise/cross_check) |
| `google_search` quality vs Tavily | ✅ Competitive on content; URL shape differs |
| `ParallelAgent` parallelises | ✅ 18s for three concurrent streams |
| **`exit_loop` reliability** | ✅ Held in both scenarios this PR |
| **Gemini's PASS-with-notes calibration** | ✅ Excellent — caught all fabricated issues, plus one bonus |
| `event.actions.escalate = False` suppression | ⬜ PR 5 |
| `output_schema=FinalBrief` reliability | ⬜ PR 5 |

Five of seven answered. The remaining two are both PR 5 territory.

## Findings to carry forward

| Finding | Implication for next PRs |
|---|---|
| Initial-generator-then-loop pattern works as documented | PR 4 rendering loop uses the same shape: `build_draft()` outside loop + `LoopAgent(sense_check, revise)` |
| Two-variant specialist factories work cleanly | If sense_check needs an "initial" vs "in-loop" variant in PR 4, use the same pattern |
| Empty cross_check_result on PASS | PR 5 orchestrator must use function_call detection, not state parsing. Same will apply to sense_check on PASS in PR 4. |
| `str(dict)` works for `{price_data}` template substitution | No need to JSON-marshal price_data. Just `str()` it before seeding state. |
| Audit revise → pass cycle takes ~30s on top of base synthesis | Budget ~60-90s for a worst-case synthesis loop (one failed iteration) in PR 5 orchestrator latency planning |
| Stale-events log noise from prior runs | ADK warning `"Event from an unknown agent: X"` appears when a session has events from agents not in the current Runner's tree. Harmless but verbose. Worth a callback-based filter in PR 5 if it bothers observability. |

## What's NOT in this PR

- Rendering layer + retry loop — PR 4
- Custom orchestrator + `FinalBrief` — PR 5
- Agent Engine deployment — PR 6

## Reproducibility

```bash
cd phase3-vertex-gemini
uv sync   # no new deps
uv run python -m briefing_agent.smoke_synthesise
uv run python -m briefing_agent.smoke_cross_check
uv run python -m briefing_agent.smoke_synthesis_loop
```

Outputs vary run-to-run (LLM non-determinism), but the
architectural patterns — exit_loop terminating the loop,
auditor calibration on real-vs-fabricated content, two-
iteration revise cycles — are stable across runs.
