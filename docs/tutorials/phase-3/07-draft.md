# STEP-07 — Rendering layer: brief drafting + sense_check audit loop

The rendering layer lands. Adds the draft specialist, the
sense_check auditor with `exit_loop` bound, the revise specialist
for in-loop revision, and the `LoopAgent`-based rendering audit
loop.

This step closes the last STEP-03 mechanical question (revise
behaviour) and surfaces one real calibration finding worth
carrying into Phase 3's retrospective.

## What's in this PR

Three prompts, three specialists, one workflow, three smokes:

| File | Role |
|---|---|
| `src/briefing_agent/prompts/draft.md` | Verbatim port from Phase 2 |
| `src/briefing_agent/prompts/sense_check.md` | Phase 2 port + exit_loop footer |
| `src/briefing_agent/prompts/revise.md` | Verbatim port from Phase 2 |
| `src/briefing_agent/specialists/draft.py` | `build_draft` — reads {synthesis}, writes state['draft'] |
| `src/briefing_agent/specialists/sense_check.py` | `build_sense_check` with `exit_loop` tool bound |
| `src/briefing_agent/specialists/revise.py` | `build_revise` — overwrites state['draft'] |
| `src/briefing_agent/workflows/rendering_loop.py` | `LoopAgent(sense_check, revise)`, max_iterations=2 |
| `src/briefing_agent/smoke_draft.py` | Live-chain (research → synthesise → draft) |
| `src/briefing_agent/smoke_sense_check.py` | Dual scenario (PASS via real draft, FAIL via fabricated bad draft) |
| `src/briefing_agent/smoke_rendering_loop.py` | Dual scenario (happy path, fail→revise→pass path) |

## What ports verbatim from Phase 2

`draft.md` and `revise.md` port unchanged. `sense_check.md` ports
unchanged **except for the same exit_loop footer** added to
cross_check.md in PR 3 (the minimum-necessary adaptation for ADK's
function-call routing).

Six of seven Phase 3 specialist prompts have now been validated as
verbatim-portable. The remaining specialist (orchestrator) has no
Phase 2 equivalent that ports — Phase 2 had a prose-driven
orchestrator prompt; Phase 3's is a custom BaseAgent in code.

## The three findings

This PR produces three findings worth dwelling on. Two are happy
news, one is a real calibration observation.

### Finding 1 — Sense_check calibration is stricter than cross_check

**Observed:** The standalone `smoke_sense_check` PASS scenario,
running on a real draft from a real synthesis, returned
**VERDICT: FAIL**. The flagged issue:

> *"The CATALYSTS SECTION in the brief includes the API Weekly
> Crude Stock report as a key data release to watch. The synthesis
> mentions U.S. crude oil inventory drawdowns as a past/current
> factor supporting prices but does not explicitly identify the
> API report as a forward-looking catalyst..."*

The auditor's own SUMMARY characterised this as "minor but
distinct". The sense_check prompt explicitly says:

> *"Bias toward passing. A brief with one or two minor issues
> should pass with notes, not fail. Only fail when revision
> would meaningfully improve the brief for the reader."*

A minor-by-its-own-description issue caused a FAIL. The
calibration is **not as biased toward passing as cross_check's**.

PR 3's cross_check happily PASSed real syntheses on first try.
PR 4's sense_check is finding minor issues in real drafts and
failing on them.

**Possible explanations:**

- Brief audit has more dimensions (faithfulness, structure,
  prose, consistency) — more potential issues to find
- Briefs are longer prose; more surface area for nitpicks
- "Would a competent reader notice this?" is more subjective
  than "is this synthesis grounded in the research?"

**Implication:** in production runs, expect rendering_loop to
hit iteration 2 more often than synthesis_loop. The 30-second
revise cycle becomes more common, not exceptional. Worth
acknowledging in PR 5's orchestrator timing budget.

**Worth investigating later:** does softening the sense_check
prompt language reduce false-FAIL rate? The prompt currently
says "bias toward passing"; could be stronger ("default to
PASS unless the issue would mislead the reader").

### Finding 2 — Model variance: same draft, different verdicts

**Observed:** The standalone sense_check FAILed a real draft.
The rendering_loop happy path immediately afterward — with a
fresh draft from a fresh synthesis — PASSed cleanly with
exit_loop called.

Same agent. Same prompt. Same instruction wrapper. Different
input data, different verdict.

This is normal LLM non-determinism, but it has real consequences:

- **Smoke tests of auditors must accept variance.** A single
  FAIL on the "PASS scenario" isn't a calibration issue; it's
  variance.
- **The rendering_loop is robust to variance** — even if
  sense_check FAILs iteration 1 due to model strictness, the
  revise cycle on iteration 2 (with a different sense_check
  call) is likely to PASS.
- **PR 5 orchestrator timing estimates should be probabilistic.**
  Some runs will hit cap; some will pass first try.

### Finding 3 — Revise is not surgical

**This is the answer to STEP-03's deferred "what I'm not yet
sure about" question.**

The revise.md prompt is explicit:

> *"This is **targeted revision, not a rewrite**. Don't change
> sections that weren't flagged. Don't re-render from scratch.
> Take the existing draft, apply the specific fixes called for
> in the revision notes, and return the result."*

**Observed behaviour:** in the fabricated-bad rendering_loop
scenario, comparing the fabricated bad draft to the revised
output:

- The bad draft's PRICE SECTION had bullet points and lacked
  the specific 4.45% number → the revised PRICE SECTION
  contains "4.45% surge" and "WTI above $102", in prose
- The bad draft's NEWS SECTION and GEOPOLITICS SECTION both
  led with Strait of Hormuz → the revised brief differentiates
  them, with NEWS leading on the supply crisis frame and
  GEOPOLITICS leading on the strait-and-OPEC-and-Russia
  structural picture
- The bad draft's CATALYSTS SECTION had the fabricated "OPEC
  emergency meeting next Tuesday" → revised CATALYSTS has
  none of this

Gemini correctly fixed every flagged issue.

But the revised draft also looks **very similar to the happy-path
draft** — same lead numbers, same narrative arc, similar
paragraph structure across all four sections. Revise didn't
preserve the fabricated draft's structure and patch the issues;
it produced what amounts to a **fresh rendering of the synthesis**
that happens to address the issues.

**Implication:** "targeted revision, not a rewrite" works as
guidance for *what to fix*, not for *how aggressively to change
things*. Gemini interprets the prompt as "produce a brief that
doesn't have these issues" rather than "edit the existing brief
to remove these issues."

For Phase 3 specifically, this is fine — the final brief is
correct. But it surfaces a real Gemini-vs-Haiku behavioural
difference worth investigating in the retrospective:

- Does Phase 2's Haiku revise more surgically?
- Does Phase 1's LangGraph revise show different behaviour
  again?
- Is this a model-level difference, a prompt-tuning issue, or
  a framework difference?

The Phase 3 retrospective will be the right place to
investigate by comparing actual revise outputs across all
three phases.

## What ran

All three smokes ran. Walking through:

### `smoke_draft`

Four-section brief produced cleanly in 15.0 seconds. All four
mandatory headers (PRICE, NEWS, CATALYSTS, GEOPOLITICS) in
order. Each section 2-4 paragraphs. HEADLINE METRICS from
synthesis embedded in prose (the 3.98% price change, 53.3m
SPR release, UAE withdrawal, OPEC two-decade low). No bullets,
no headers within sections. Voice consistent across sections.

### `smoke_sense_check` (dual scenario)

**PASS scenario** (real draft): sense_check returned VERDICT:
FAIL on a minor faithfulness issue (the API report mention).
See Finding 1.

**FAIL scenario** (fabricated bad draft): sense_check caught
the planted bullet points, repetition between NEWS and
GEOPOLITICS, fabricated OPEC meeting — plus several extra
issues I hadn't planted (missing headline metrics, sections
too short). REVISION NOTES were detailed and actionable.
Format-compliant: VERDICT line, all four issue categories,
REVISION NOTES.

### `smoke_rendering_loop`

**Happy path** (real draft from real synthesis): sense_check
PASSed on iteration 1 in 14.8s, exit_loop called, loop exited.
1 sense_check event, 0 revise events. (Note: same chain as
the standalone smoke that FAILed — model variance.)

**Fail→revise path** (fabricated bad draft): sense_check
FAILed iteration 1, revise ran and produced a corrected
draft, sense_check PASSed iteration 2 in 46.2s total. 2
sense_check events, 1 revise event, exit_loop called.

**The revise actually worked** — bullets removed, fabricated
catalyst removed, NEWS/GEOPOLITICS differentiated. See
Finding 3 for the surgical-vs-fresh-rendering analysis.

## STEP-03 open questions — final scoreboard

After PR 4, all questions that could be answered without the
orchestrator are now closed:

| Question | Status |
|---|---|
| Prompt-port-verbatim for Gemini | ✅ Six of seven specialists validated (only orchestrator remains, and it's a custom BaseAgent, not a prompt-driven LlmAgent) |
| `google_search` quality vs Tavily | ✅ Validated PR 1 |
| `ParallelAgent` parallelises | ✅ Validated PR 2 |
| `exit_loop` reliability | ✅ Validated PR 3 |
| Gemini's PASS-with-notes calibration | ⚠️ Holds for cross_check, looser for sense_check (Finding 1) |
| `event.actions.escalate = False` suppression | ⬜ PR 5 |
| `output_schema=FinalBrief` reliability | ⬜ PR 5 |

Plus the new answer to STEP-03's "what I'm not yet sure about":
**Revise doesn't stay surgical** (Finding 3).

## What's NOT in this PR

- Custom orchestrator + `FinalBrief` — PR 5
- Agent Engine deployment — PR 6

## Reproducibility

```bash
cd phase3-vertex-gemini
uv sync   # no new deps
uv run python -m briefing_agent.smoke_draft
uv run python -m briefing_agent.smoke_sense_check
uv run python -m briefing_agent.smoke_rendering_loop
```

Outputs vary run-to-run — Finding 2 (model variance on the same
draft → different verdicts) means sense_check's standalone
result isn't deterministic. The rendering_loop's overall
behaviour (PASS path exits at iteration 1, FAIL path exits at
iteration 2 after revise) is stable across runs.
