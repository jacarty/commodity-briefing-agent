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
