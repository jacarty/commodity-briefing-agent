# STEP-06 — The rendering layer

The rendering layer is live. `draft` reads synthesis and produces
a four-section briefing; `sense_check` audits the rendered brief
against the synthesis and emits a `VERDICT: PASS / FAIL` line;
`revise` applies sense_check's revision notes to produce a
targeted re-rendering when sense_check fails.

This step covers PR 4 — three specialists built and smoke-tested,
plus a smoke-test design improvement (in-run side-by-side
comparison via difflib) that answered the one open behavioural
question from STEP-03's design.

## What I did

- Built `draft` as the first rendering specialist. Same tools-less
  template as synthesise. Four mandatory section headers in the
  output (PRICE SECTION, NEWS SECTION, CATALYSTS SECTION,
  GEOPOLITICS SECTION). Phase 1's editorial constraints ported
  verbatim — no bullets, no internal headers, no weasel phrases,
  embed metrics in prose, inverted pyramid per section.
- Built `sense_check` as the second auditor. Same `VERDICT: PASS /
  FAIL` opening-line convention as cross_check. Four issue
  categories (FAITHFULNESS, STRUCTURE, PROSE, CONSISTENCY) plus
  REVISION NOTES paragraph for the reviser.
- Built `revise` as the targeted re-rendering specialist. Same
  output structure as draft. Prompt bolds the
  *"targeted revision, not a rewrite"* instruction — the lesson
  Phase 1 found load-bearing for keeping revise distinct from
  draft.
- Wrote a live-chain smoke test for draft (research × 4 →
  synthesise → draft, print result).
- Wrote a dual-scenario smoke test for sense_check using the
  fabrication-injection pattern established in PR 3 — but adapted
  for faithfulness violations instead of grounding violations.
- Wrote a chained smoke test for revise that uses sense_check's
  actual REVISION NOTES output as revise's input. Updated the
  smoke test mid-PR to include in-run side-by-side comparison
  with per-section difflib similarity ratios after the first
  version couldn't definitively answer the targeting question.
- Logged five observations in `docs/observations.md`.

## What I learned

### The specialist template scales across all four shapes now

After PR 4, every specialist type in the design has been built:

- **Plain tool** (fetch_price): `@tool`-decorated function, no LLM
- **Tool-equipped research specialist** (3 of these): Strands
  Agent with bound tools
- **Interpretive specialist** (synthesise): tools-less Agent
  reading structured prose, producing structured prose
- **Auditor** (cross_check, sense_check): tools-less Agent
  returning VERDICT line + categorised issues
- **Renderer** (draft): tools-less Agent producing 4-section
  prose
- **Targeted re-renderer** (revise): tools-less Agent with
  same output shape as draft but acting on flagged issues

The agent factory is the same shape across all the LLM-backed
specialists. Variations: `tools=[]` vs `tools=[tavily_search]`,
different prompts, different descriptions. The factory pattern,
`callback_handler=None`, and the model/region wiring are
identical.

This is a real architectural property worth naming: the agents-
as-tools pattern absorbs *type-of-job* variation entirely into
prompts. The Python code surface for adding another specialist
is twelve lines.

### Phase 1's editorial constraints port verbatim

draft's prompt has the most detailed editorial guidance in the
project — voice instructions, anti-patterns, "what to avoid,"
inverted pyramid, no metric repetition, no section repetition.
Almost all of that is verbatim from Phase 1. The mechanical
adaptations were the same as elsewhere: strip the template
variables, add an output-format section.

Two smoke runs and the drafts looked like real briefs. Phase 1's
voice held; the metrics were embedded in prose with context, not
bullet-listed; sections didn't repeat each other; each section
led with its most important content. The prompt was doing what
the prompt is supposed to do.

This continues to validate STEP-03's claim that prompt-level
lessons port unchanged. The lessons are about how Claude reasons
under instruction, not about LangGraph state plumbing.

### sense_check matches cross_check's auditor pattern exactly

Both auditors validated with the same fabrication-injection test
pattern. Both returned `VERDICT: PASS` cleanly on legitimate
input and `VERDICT: FAIL` cleanly on corrupted input. Both
correctly used their issue categories (cross_check: consistency
/ calibration / grounding; sense_check: faithfulness / structure
/ prose / consistency). Both produced actionable downstream
output (cross_check: re-research targets; sense_check: revision
notes).

The two auditors are structurally identical — same template,
same VERDICT line, same output discipline. The difference is
entirely in what they're checking and against what. Auditor as a
specialist *shape* is now a well-understood thing in the project.

If we ever needed a third auditor (e.g., one that audits the
final delivered brief against some downstream constraint), the
template is ready.

### Pass-bias produces correct "PASS with notes" calibration

sense_check's PASS scenario returned `VERDICT: PASS` while still
surfacing a STRUCTURE issue (the Xi-Trump summit emphasis could
be sharpened). The REVISION NOTES were explicitly labelled
"Optional tightening only."

This is exactly the right calibration. The competent-reader bar
worked. The auditor:

- Recognised the issue as real but minor
- Didn't fail on stylistic preference
- Surfaced the note for awareness rather than action

The orchestrator should treat PASS as "proceed to delivery"
regardless of optional notes. If we ever want to use the optional
notes (e.g., feed them to revise as polish), that's future
enhancement territory. For now, PASS = ship.

### revise stays targeted (the design question STEP-03 explicitly opened)

STEP-03 listed five things to watch for during the build. One
was: *"Does revise stay distinct from draft in practice? If
revise fires but produces fresh drafts instead of targeted fixes,
the prompt isn't holding the distinction and we may need to
collapse the two."*

The answer is: yes, revise stays distinct. The updated smoke test
with in-run side-by-side comparison made this mechanical to
verify:

```
PRICE SECTION          100.00%   verbatim
NEWS SECTION           100.00%   verbatim
CATALYSTS SECTION       93.43%   trivial changes
GEOPOLITICS SECTION    100.00%   verbatim
```

The NEWS SECTION at 100% needs unpacking. sense_check asked for
two changes: delete the injected opening sentence from NEWS
SECTION, and reword one sentence in CATALYSTS SECTION about
frontrunning risk. The corruption was a *prepend* — the original
draft's NEWS SECTION already had the correct opening sense_check
asked for. revise removed exactly what was prepended and left
everything else untouched. Net result: revised NEWS SECTION
identical to original draft NEWS SECTION.

The 93.43% in CATALYSTS reflects the one sentence rewording,
exactly as instructed. Surgical.

The bolded *"targeted revision, not a rewrite"* prompt
instruction is sufficient. Phase 1's lesson — that revise drifts
toward full re-rendering without explicit instruction otherwise
— ports unchanged and the same mitigation works.

### A smoke-test methodology lesson worth keeping

The first version of smoke_revise.py couldn't answer the
targeting question. I'd intuitively compared revise's output
against memory of a *different* chain run's draft and concluded
revise was drifting. That comparison was invalid — different
chain runs produce different drafts, all reasonable. The drift I
thought I saw was just normal between-run variation.

The fix was a smoke test that prints both versions from the
*same chain run* plus per-section similarity ratios via
difflib.SequenceMatcher. With that, the answer becomes mechanical.

This is a general pattern worth keeping for any future specialist
that's supposed to preserve content it wasn't asked to change:

- Always compare within a single chain run, not against memory or
  prior runs
- Print the comparison side-by-side
- Add a mechanical metric (similarity ratio) plus a categorical
  verdict
- Have the test state the expected verdicts as a check on
  interpretation

The thresholds I picked (verbatim ≥ 0.98, trivial ≥ 0.85, partial
≥ 0.50, substantial < 0.50) are heuristic but worked first try.
The Python stdlib's `difflib.SequenceMatcher` is sufficient.

### Three STEP-03 open questions closed in PR 4 alone

Looking at STEP-03's "things we'll be watching for" list, PR 4
landed strong evidence on three of them:

- **Does text-native synthesise reliably produce the
  cross_stream_signals section?** — closed in PR 3 (positive,
  mandatory-section instruction works). PR 4 ran the chain four
  more times; CROSS-STREAM SIGNALS still substantive every time.

- **Is the VERDICT: PASS/FAIL opening line interpreted correctly
  by the orchestrator?** — closed in PR 3 for cross_check,
  re-validated in PR 4 for sense_check. The line works.

- **Does revise stay distinct from draft in practice?** — closed
  in PR 4 (positive, prompt instruction sufficient, side-by-side
  smoke test mechanically confirms targeting).

Two named open questions remain from STEP-03:

- **Does the orchestrator reliably enforce two retry loops from
  prose alone?** — not testable until the orchestrator lands in
  PR 5.
- **Does the orchestrator manage input-string assembly reliably?**
  — not testable until PR 5.

Both are the orchestrator-level questions, and both are PR 5's
core test.

## What surprised me

- **NEWS SECTION at 100% similarity in the revise test.** When the
  diff summary first came up, I almost interpreted it as "revise
  didn't actually apply the fix." Then I traced through sense_check's
  REVISION NOTES against the original draft and realised: the
  corruption was a prepended sentence, the original opening was
  already what sense_check asked for, and revise correctly removed
  the prepended sentence. The result matches the *original*, not
  some new version, because the original was already correct. This
  is exactly the targeted-revision discipline we wanted — the most
  precise possible result.

- **How much my prior reading was wrong.** I'd written an entire
  observation entry claiming revise was drifting toward broader
  rewriting, with implications for whether we'd need to tighten
  the prompt. That entry was based on cross-run comparison that
  wasn't valid. The corrected smoke test made the truth mechanical,
  and the truth was the opposite of my interpretation. Worth keeping
  this admission visible — both because it's honest about how easy
  it is to misread a system at this scale, and because the lesson
  about same-run comparison is genuinely useful.

- **revise's behaviour without any extra prompt engineering.** I'd
  been preparing arguments for prompt tightening if revise drifted
  — stronger imperatives, explicit echo requirements, structural
  constraints. None of that was needed. The single bolded line in
  the prompt was sufficient. Phase 1's lesson generalises
  unmodified.

- **The CATALYSTS 93.43% similarity is exactly right.** One sentence
  rewording, in the section sense_check flagged, with no spillover
  to the other paragraphs in that section. That's the kind of
  precision typed contracts can enforce mechanically; doing it with
  prompt instruction alone is a real success of the text-native bet.

## What's NOT decided yet

Both the items here are about the orchestrator (PR 5):

- **Whether the orchestrator can manage the two retry loops in
  prose.** STEP-03 named this as the hardest test of model-driven
  orchestration. Untestable until the orchestrator exists.
- **Whether the orchestrator manages input-string assembly
  reliably.** The smoke tests have all done assembly directly in
  Python helpers; the orchestrator will encode this in prompt
  instructions. Whether the model reliably packages four research
  outputs + price + spec into a single input for synthesise (and
  similarly for downstream specialists) is the open question.

## Open questions

- **Cost shape at full orchestrator scale.** Five smoke runs in PR
  4 came in at ~3-6 cents each. The orchestrator full run will be
  bigger (8 specialists, some potentially called twice during retry
  loops). Probably 10-15 cents per orchestrator invocation. Worth
  tracking when it lands.
- **Whether the optional REVISION NOTES from a PASS verdict should
  feed forward.** sense_check's pass-with-notes calibration is
  working, but the notes are currently advisory only. If we ever
  want them treated as polish, that's a small enhancement to the
  orchestrator's prompt.
- **Whether to factor `assemble_*_input` helpers into a shared
  module.** Five smoke tests each have their own assembly logic.
  The orchestrator will likely encode this work in prompts, but if
  we keep multi-specialist smoke tests around (for partial chain
  testing), shared helpers would dedupe the code.

## Glossary

- **Targeted revision** — The discipline of changing only what was
  flagged, leaving everything else verbatim. The behavioural
  constraint Phase 1 found load-bearing for keeping revise distinct
  from draft. Validated in Phase 2 via the bolded prompt instruction
  alone.
- **In-run side-by-side comparison** — A smoke test pattern where
  the original and revised outputs come from the same chain
  execution and are printed together for direct comparison. The
  alternative — cross-run comparison or comparison against memory
  — is invalid because each chain run produces different
  intermediate artifacts. The lesson: any "did this specialist
  preserve content?" question requires in-run comparison.
- **Similarity ratio** — `difflib.SequenceMatcher.ratio()` between
  two strings, in [0, 1]. Used in smoke_revise to mechanically
  verify whether a section was preserved (≥0.98) or modified.
  Thresholds are eyeball-calibrated but worked first try.
- **Pass with notes** — An auditor verdict pattern where
  `VERDICT: PASS` is returned alongside optional STRUCTURE or
  similar notes labelled as advisory rather than required. The
  brief ships; notes are available if downstream wants to act on
  them, but routing-wise PASS means proceed.
