# STEP-07 — Synthesise: the first reasoner

## What I did

- Implemented `synthesise` — first node that reasons over state without
  doing new research. Reads all four research outputs plus
  `briefing_spec` and `research_plan`; emits a structured `Synthesis`.
- Designed a `Synthesis` schema with five fields:
  `dominant_narrative`, `price_interpretation`, `cross_stream_signals`,
  `risks_to_view`, `headline_metrics`. Strings except for the metrics
  list.
- No tools, no search. Just `with_structured_output`. The simplest LLM
  pattern, doing the most conceptually demanding work in the agent.
- Wrote the prompt to push against the model's natural hedging
  tendencies — anti-weasel instructions, "commit where research
  supports commitment," structured place for hedging
  (`risks_to_view`).

## What I learned

### Reasoners are inverse to research nodes

Research nodes take an unstructured prompt and produce structured data.
Synthesise inverts this: it takes structured research data and produces
interpretive content. Same `with_structured_output` mechanism, opposite
direction.

This is the conceptual shift between "fetch and shape facts" and
"reason over facts." All the audit nodes that come later (cross-check,
sense-check) are reasoners too. Synthesise is the first one and sets
the pattern.

### Cross-stream signal is a first-class field

I considered making the synthesis schema mirror the four briefing
sections — one field per section. Decided against it. Reason: the most
interesting analysis happens *between* the sections, not within them.
"Price is down 4%" is a number; "price is down 4% AND news shows
ceasefire signals AND geo flags reduced Hormuz risk" is a coherent
story.

The `cross_stream_signals` field is dedicated space for that
inter-stream story. The model knows to look for it because it has a
field shaped like that to fill.

This pays off in the brief that draft eventually produces. The
geopolitics section — which gets to lean on `cross_stream_signals` —
ends up doing the most analytically interesting work in the brief,
because the field already forced the reasoning.

### Anti-weasel prompts work

Default LLM behaviour, especially for analytical writing: hedge
everything. "Various factors influence the market." "Several
considerations are at play." "It's important to note that..."

The prompt explicitly forbids these phrases unless the genuine signal
is mixedness itself. It also designates `risks_to_view` as the
*only* field that hedges, with everything else expected to commit.

Empirical: synthesis output is meaningfully more declarative with
these instructions than without. The dominant narrative reads as a
view, not as a survey. When real uncertainty exists, it lands in
`risks_to_view` where it belongs.

The lesson: prompts can shape voice. "Avoid weasel phrases" is a
weak instruction; "the dominant narrative is the place to commit; the
risks field is the place to hedge" is a structural one that the model
follows.

### Headline metrics force concreteness

`headline_metrics` is a list of 3-5 specific facts. The instruction is
that these *must* appear in the eventual brief. The drafter is
expected to weave them into prose, not bullet-list them.

The mechanism is clever: the schema makes the model produce a list of
specific, sourced facts as part of synthesis. Those facts then become
required content for draft. The synthesis stage is doing fact-selection
work that might otherwise be left to the drafter.

Without this field, the brief tends toward generic ("oil prices fell on
geopolitical news"). With it, the brief lands specific numbers in
context ("WTI fell 4.5% on US-Iran ceasefire reports").

### Reading the research plan, not just the research

Synthesise reads `research_plan` alongside the actual research outputs.
This seemed unnecessary at first — the plan is what was *asked for*,
not what came back.

But knowing what each stream was asked to find lets synthesise
distinguish "research found nothing" from "research wasn't asked the
right question." If news comes back light, synthesise can see the plan
asked for X, only Y came back, and weight accordingly. Without the
plan, the model has to guess whether sparse research means quiet day
or misdirected research.

### Synthesis is the first place upstream design pays off

Geo emits themes with confidence ratings. News emits items with
direction enums. Catalysts emits events with importance ratings.

Synthesise reads all of them and *uses the ratings*. Output explicitly
weights high-confidence geo themes more heavily, treats neutral news
items as background context, leads on high-importance catalysts. The
first paragraph of dominant_narrative on a typical run reads like
someone who has internalised the per-stream calibration data.

This wouldn't work if upstream just produced flat lists of facts. The
schema decisions in STEP-04, 05, 06 — Literal enums, multiple
calibration axes — are what makes synthesise reasoning possible. The
investment compounds.

## What surprised me

- How much editorial latitude the model needs to do good synthesis
  work, and how much *structure* the prompt provides without
  constraining the latitude. Five fields is enough to shape the
  output without dictating it.

- That `risks_to_view` ends up being one of the most useful fields in
  the eventual brief. Designating "the hedge field" makes the rest of
  the synthesis declarative *and* makes the hedges land in a single
  reviewable place.

- That asking the model to read both the research plan and the
  research outputs improves quality noticeably. I expected one or the
  other.

## Open questions

- Should `headline_metrics` be typed (number + unit + context) rather
  than free strings? Probably. For Phase 1 the strings are fine; if
  the brief ever needs to render metrics in tables, structured form
  becomes necessary.

- Is there a case for letting synthesise fail if the research is too
  thin? Currently it produces a synthesis no matter how empty the
  inputs. A "no clear story today" output would be more honest in
  some cases.

## Glossary

- **Reasoner node** — A node that produces interpretive output by
  reasoning over state, without external research or tool calls.
  Synthesise, cross-check, sense-check all count.
- **Cross-stream signal** — Insight produced by reading multiple
  research streams together. Often more valuable than any single
  stream's findings.
- **Anti-weasel prompt** — Prompt instructions that push back against
  the model's tendency to hedge through generic phrasing.
  Distinguished from instructing the model not to hedge at all —
  hedging is fine in its designated place.
