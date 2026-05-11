# Phase 2 — Build-period observations

A running log of things observed while building Phase 2. The text-
native bet from STEP-03 means we're trusting prose conventions and
prompt instructions to do work that Phase 1's typed schemas did
automatically. This file is where we capture observations of how
that's going — the small leaks, the surprises, the patterns —
while they're fresh.

The eventual STEP retrospective (whichever step closes out PR 1, or
a Phase 2 retrospective) draws from here. Without this file, the
observations live only in chat transcripts and PR descriptions and
get lost.

## Format

Each entry: dated heading, what was observed, the run that surfaced
it, what we did about it (if anything), what it implies for later.

---

## 2026-05-10 — research_news preamble drift

**Observed**: Across three smoke-test runs, the news specialist
consistently opened its response with a short preamble (e.g.
*"Based on my search results, here are the most important oil-
related news items from the last 24 hours:"*) before `ITEM 1`,
despite the system prompt saying *"No preamble, no closing
commentary."*

**Variation**: Run 2 also wrapped the output in triple-backtick
code fences; runs 1 and 3 didn't.

**What we did**: Nothing. Logged here.

**Why not tighten the prompt yet**: The drift is mild and the
orchestrator parser can skip leading lines until it hits `ITEM N`.
Tightening the prompt now would be solving a problem we haven't
hit yet. Watch whether the same pattern shows up in other
specialists when they land.

**Implication**: Text-native instructions like "no preamble" are
*soft* constraints. The model interprets them loosely. We should
expect minor presentation drift across all specialists and design
the orchestrator parsers to be lenient about leading/trailing
prose.

---

## 2026-05-10 — research_news direction-call instability

**Observed**: Same news event got opposite direction calls across
runs. The global stockpile drawdown was tagged `reverses_trend`
in run 1, `supports_trend` in runs 2 and 3.

**What we did**: Nothing. Logged here.

**Why not tighten the prompt yet**: Phase 1's retrospective flagged
the same soft spot — direction/confidence calls are inherently
interpretive and don't stabilise without much stronger framing
than "supports_trend / reverses_trend / neutral." Could tighten
with explicit definitions and worked examples in the prompt; not
worth it if the cross_check auditor catches material problems
downstream.

**Implication**: Direction tags are noisier than Phase 1's typed
contracts implied. They're useful as the model's *current*
interpretation, not a stable label. cross_check is the layer that
catches when the interpretation is genuinely wrong (claim flips
the trend it's supposed to support).

---

## 2026-05-10 — Strands streams to stdout by default

**Observed**: STEP-02 hello-world printed its response twice
because Strands' `Agent.__call__` streams to stdout *and* returns
the response object.

**What we did**: All Phase 2 specialists are constructed with
`callback_handler=None`, which silences stdout streaming for that
agent. Set in the `Agent(...)` constructor; applies to all
invocations of that instance.

**Implication**: Already resolved. Logged here so the pattern is
discoverable from this file rather than from spelunking through
multiple step docs. The orchestrator (when it lands) will need an
explicit decision on whether *it* should stream — for dev runs we
probably want to see top-level orchestrator reasoning; for
deployed runs probably not.

---

## 2026-05-11 — Preamble drift is consistent across all research specialists

**Observed**: PR 2 smoke runs (catalysts × 2, geo × 2) all opened
with "Based on my research..." or similar preambles before the
first structured item. Same pattern as research_news in PR 1. So:

- research_news (3/3 runs): preamble present
- research_catalysts (2/2 runs): preamble present
- research_geo (2/2 runs): preamble present

7 out of 7 runs across three specialists. Consistent.

**What we did**: Nothing. Confirmed the implication.

**Implication**: This is structural to how Claude (via Bedrock)
responds to tool-equipped agent prompts asking for structured
prose output. Not a per-specialist quirk we can prompt-engineer
away cheaply. The right place to handle it is the orchestrator's
parser: skip leading content until the first structural marker
(`ITEM N`, `EVENT N`, `THEME N`, etc.). Plan for this when the
orchestrator lands.

---

## 2026-05-11 — research_catalysts: duplicated EVENT block

**Observed**: One catalysts smoke run (run 1) produced its EVENT
block twice — once inline in the prose explanation, then again
wrapped in triple-backtick code fences at the end. Same content,
same field values, but a naive parser scanning for `EVENT N`
markers would see two events when there's really one.

This is qualitatively different from the preamble drift — the
preamble is *before* the structured content and trivially
skipped. The duplication is *within* the structured content and
has parse-correctness implications.

**What we did**: Nothing yet. Logged.

**Why not tighten the prompt yet**: Hit once across PR 2's runs.
Could be a stable pattern (the model sometimes "draft and final"
inside one response) or could be a one-off triggered by the
empty-day scenario where the model was reasoning about whether
to report any event at all. Need more data — watch in subsequent
runs and in the orchestrator end-to-end.

**Implication**: The orchestrator parser may need to dedupe
structured markers — e.g., if `EVENT 1` appears twice with
identical field values, treat as one event. Less appetising than
the preamble case (we'd be papering over model behaviour rather
than just being lenient about wrapping prose). A stronger prompt
instruction may be needed if this persists: *"Produce the
EVENT/ITEM/THEME blocks exactly once. Do not repeat them inside
code fences or as separate sections."*

If it persists, this becomes the strongest signal yet for "hybrid
where quality forces it" — wrapping research specialists in
`structured_output_model` via a custom `@tool` would eliminate
duplication-class parse problems entirely.

---

## 2026-05-11 — research_catalysts: empty-day judgement is interpretive

**Observed**: Two runs of research_catalysts on the same date (May
11, 2026, a Monday) produced different decisions:

- Run 1: returned one `EVENT 1` for US Existing Home Sales tagged
  `importance: low`
- Run 2: reasoned through the same available events and concluded
  `NO EVENTS`, on the grounds that domestic housing data isn't
  an oil-market catalyst even at low importance

Both decisions are defensible. The first is more conservative
(report everything available, let the orchestrator decide what
matters); the second is more editorial (apply judgement at
research time about what's worth flagging).

**What we did**: Nothing. Logged.

**Why not tighten the prompt yet**: Phase 1 absorbed this
ambiguity in the `importance` field — both behaviours produce
the same downstream signal (a low-importance event vs nothing).
In text-native, the decision lives in whether to emit an
EVENT block at all. The orchestrator can either consume both
shapes (handle `NO EVENTS` and "all entries are importance: low"
equivalently) or we can tighten to one convention.

**Implication**: The catalysts prompt would benefit from explicit
guidance on the threshold for emitting an event vs returning
`NO EVENTS`. Something like *"Emit any scheduled event with
plausible oil-market relevance, even if importance is low.
Return `NO EVENTS` only when the day has genuinely no oil-relevant
scheduled releases."* But — defer until we see how the orchestrator
consumes both shapes. If it handles both gracefully, leave the
prompt alone.
