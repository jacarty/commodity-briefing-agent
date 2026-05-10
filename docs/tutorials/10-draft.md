# STEP-10 — Draft: prose at last

## What I did

- Implemented `draft` — first node that produces actual prose. Reads
  synthesis + briefing_spec; emits a `Brief` with four section
  strings: `price_section`, `news_section`, `catalysts_section`,
  `geopolitics_section`.
- Wrote `prompts/draft.md` with intent-based section guidance, voice
  instructions, and an explicit anti-pattern list (no bullets, no
  internal headers, no weasel phrases).
- Used `with_structured_output(Brief)` — the same pattern as
  synthesise, despite producing prose. The structure is at the
  section level, not within sections.
- Verified the brief reads as analyst commentary, not a bullet-list
  dump. Voice consistent across sections, headline metrics embedded
  in prose with context, sections distinct rather than redundant.

## What I learned

### Structured at the section, free within

The `Brief` schema is just four strings. Each is a full prose
section, 2-4 paragraphs.

Two extreme alternatives I considered:

- *Strict templating* — fill prose into fixed slots like `{lead}`,
  `{key_metric}`, `{closing}`. Mechanical but predictable.
- *Free prose* — single output string, model chooses the structure.
  Maximally expressive, hard to audit.

I picked the middle: section-level structure with free prose within.
Reasons:

- Sense-check (the auditor) can audit each section against synthesis
  independently
- Drafter is forced into the four-section structure, which the
  briefing_spec demands
- Within each section, the model has editorial latitude — what to
  lead with, how to weave in metrics, where to cite vs paraphrase

Most production reporting systems land on something like this. Strict
templates feel mechanical; free prose is hard to QA.

### Section guidance is intent, not field-mapping

The prompt could have prescribed exactly which synthesis fields feed
which section: `price_section` ← `price_interpretation` +
metrics; `news_section` ← `dominant_narrative`; etc. I considered
this and rejected it.

Reason: the dominant story varies by day. Some days it's a price
story, some days it's geopolitics, some days news. A fixed mapping
fails on those edge cases.

Instead, the prompt describes the *intent* of each section:
"price_section: what happened in price action and what it means; lead
with the day's move, then interpret it." The model gets the full
synthesis and decides what content fits where.

This is the right level of latitude for the task. Tighter
constrains the analyst. Looser produces unstructured essays.

### Voice instructions need to be concrete

"Professional" is not a voice instruction. "Senior analyst briefing
colleagues — direct, evidence-led, professional but not stuffy" is.

The model produces meaningfully different prose when given a concrete
persona to write as. Compare:

- *Professional*: "Today saw notable movement in oil markets, with
  prices ending the day at slightly elevated levels following a
  period of intraday volatility."
- *Senior analyst briefing colleagues*: "WTI closed up 0.85% at
  $96.10 after a volatile session. The move masks deeper uncertainty:
  the intraday range was 7.9%."

Same content. Wildly different texture. The first is filler; the
second is a brief.

### Embed metrics, never bullet-list them

The prompt says: "Headline metrics must appear in the brief, but
embedded in prose with context, not bullet-listed."

Without this instruction, the model wants to produce a "Key Numbers"
section with bullets. That makes the brief feel like a dashboard.

With the instruction, the same metric ("WTI -4.5% on the day") lands
inside a sentence that gives it context ("WTI fell 4.5% on US-Iran
ceasefire reports — the largest single-day drop since the rally
began"). Same fact, more useful.

The lesson: dashboards report; briefs analyse. The format reflects
the goal.

### Anti-patterns matter as much as positive instruction

The "what to avoid" list:
- No bullet points
- No headers within sections
- No "various factors" / "several dynamics"
- No restating the dominant narrative across sections
- No repeating metrics

Each is an LLM default behaviour. Not naming them means the model
defaults to them. Naming them prevents the failure mode.

Same pattern as in cross-check ("what is NOT a cross-check issue") and
geo ("what to skip"). Negative instructions have outsized impact when
the failure mode is a default behaviour.

### Inverted pyramid produces good leads

The prompt asks for inverted-pyramid structure: the most important
content first, supporting detail second.

Output reflects this. First sentences across the four sections
typically carry the actual news of the section. A reader who only
reads the first sentence of each section walks away informed.

This is journalistic convention, but worth naming explicitly because
the model defaults to "set up the context, then present the finding,"
which works for essays and fails for briefs.

## What surprised me

- That `with_structured_output` produces prose this well. I expected
  to reach for free-form generation with post-processing. The
  schema-level approach worked first-time.

- How much editorial work the synthesis stage was already doing. By
  the time draft runs, most of the analysis is done; draft is mostly
  rendering. The "two-stage analyse-then-render" split is right.

- That `headline_metrics` from synthesis genuinely show up in the
  brief, naturally embedded. The model is taking that schema
  obligation seriously.

## Open questions

- Should draft ever consult the original research, or strictly the
  synthesis? Currently strict on synthesis. Argument for adding
  research access: draft could quote sources directly rather than
  relying on synthesis to surface the right detail. Argument
  against: synthesis is supposed to be the source of truth at this
  stage; adding research access undermines that.

- Is 2-4 paragraphs per section the right length? Currently it's a
  prompt instruction. Could be a soft schema constraint via
  description text.

## Glossary

- **Inverted pyramid** — Journalistic structure: most important
  content first, supporting detail later. Lets readers stop reading
  early without missing the lede.
- **Section-level structure** — Schema constrains output shape at
  section boundaries (four named sections) but lets the model write
  freely within each section. Middle ground between rigid templates
  and unstructured prose.
- **Embedded metric** — A specific number presented inside prose with
  context, not in a bullet or table. Brief-style; contrasts with
  dashboard-style.
