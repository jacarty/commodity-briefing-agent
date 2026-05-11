# STEP-04 — Research data sources

The four research data sources are live. One plain tool (`fetch_price`)
and three specialist agents (`research_news`, `research_catalysts`,
`research_geo`), each invokable end-to-end and returning the kind of
output the orchestrator will eventually consume.

This step covers two PRs:

- **PR 1 (foundations)**: `fetch_price` + `research_news` + the
  prompt-loading scaffolding + Strands streaming control via
  `callback_handler=None`.
- **PR 2 (research specialists)**: `research_catalysts` +
  `research_geo`, applying the patterns established in PR 1.

Treating both as one step rather than two because they're a coherent
unit — the four data sources the briefing depends on. The patterns
that emerged are the same patterns whether the specialist is the
first or the third.

## What I did

- Built `fetch_price` as a plain `@tool`-decorated function wrapping
  yfinance. No LLM. Phase 1's `PriceSnapshot` shape ported verbatim.
- Wrote `load_prompt` and the `prompts/` directory convention,
  ported from Phase 1 unchanged.
- Built `research_news` as the first Strands `Agent` specialist:
  `name`, `description`, system prompt from markdown,
  `tools=[tavily_search]`, `callback_handler=None`. Factory function
  rather than module-level constant.
- Built `research_catalysts` and `research_geo` to the same template
  in PR 2 — same shape, different prompts and descriptions.
- Adapted each Phase 1 research prompt to text-native: stripped the
  state-driven template variables (`{feedback}`, `{instructions}`,
  `{target_date}`, `{commodity}`), added an explicit output-format
  section with structural markers (`ITEM 1`, `EVENT 1`, `THEME 1`),
  added an explicit `NO EVENTS` marker for catalysts' empty-day case.
- Wrote a smoke test runner for each (`smoke_<name>.py` invoking
  the specialist with a sample input and printing the output).
- Logged build-period observations in `docs/observations.md` as
  patterns emerged across seven smoke runs.

## What I learned

### The specialist template is small and stable

Every Strands specialist agent in Phase 2 is going to look like
this:

```python
def build_research_news() -> Agent:
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)
    return Agent(
        name="research_news",
        description=DESCRIPTION,
        system_prompt=load_prompt("news"),
        model=model,
        tools=[tavily_search],
        callback_handler=None,
    )
```

Eight lines, plus the `DESCRIPTION` constant and the module imports.
The variations between specialists are: `name`, `description`,
`system_prompt`'s prompt file, and `tools=[]` (whether Tavily is
bound or not — the renderers won't have it, the auditors won't have
it).

This is a much smaller surface than Phase 1's per-node functions,
which carried state-reading and state-writing logic for every node.
The specialist factory pattern absorbs the framework-level
boilerplate; the specialist's *behaviour* is entirely in its prompt
and its bound tools.

### Factory functions over module-level constants

Each specialist is a function (`build_research_news()`) returning a
fresh Agent, not a `research_news = Agent(...)` at module level.

The reason: tests and smoke runners can build instances with
different config (cheaper model, different region) without import-
time side effects. We don't have that need yet, but the cost of
the factory pattern is essentially zero and refactoring eight
specialists from constants to factories later would be tedious.
Establish the pattern at specialist one; carry it forward.

This is also Phase 1's lesson about model-factory abstraction
landing one PR earlier than Phase 1 did. Phase 1's retrospective
flagged "build a `model_factory` abstraction from PR 1" as a
Phase 2 follow-through. We're doing it.

### Prompt adaptation is mechanical, not editorial

Every Phase 1 research prompt had four state-driven template
variables: `{target_date}`, `{commodity}`, `{instructions}`, and
`{feedback}`. The Phase 1 planner produced `instructions`,
re-research produced `feedback`, the graph runtime supplied the
date and commodity.

In Phase 2, none of those template variables exist at the prompt
level. The orchestrator passes runtime context via the *input
string* when it calls the specialist. The specialist's system
prompt is now standing instructions — what kind of research the
specialist does, what output format it produces, what to skip —
not a template assembled per-invocation.

The mechanical changes per prompt:

- Strip `{target_date}`, `{commodity}` — hardcoded to "oil market"
  since this project is oil-specific
- Strip `{instructions}` — orchestrator passes these as runtime
  input
- Strip `{feedback}` — same; if re-research is needed, the
  orchestrator includes feedback in the runtime input
- Add an "Output format" section showing the expected text shape
  with structural markers
- Add an explicit "No preamble, no closing commentary" instruction
  at the end (with mixed success — see observations below)

The *editorial* content of each prompt — what to look for, what to
skip, calibration guidance like geo's "low is a valid and useful
rating" — ported verbatim. That part is about how Claude reasons,
not about framework mechanics.

### Tavily lives on the specialist that needs it

The research specialists each have `tools=[tavily_search]` directly:

```python
tools=[tavily_search]
```

The orchestrator never sees Tavily. The reason was established in
STEP-03: research-domain judgement (how to phrase a search for
news vs catalysts vs geopolitics) lives with the specialist that
has the domain knowledge. If Tavily were on the orchestrator, the
orchestrator would have to encode three different search strategies,
diluting its role.

In practice this works cleanly. The specialists invoke Tavily 1-3
times per call, each with a query phrased for their domain. Tavily
returns ranked URL+snippet results; the specialist reasons over
them and writes its structured prose response.

### `callback_handler=None` for every specialist

Solved the streaming problem from STEP-02. Every specialist
constructor includes `callback_handler=None`, which prevents the
agent from streaming its response to stdout. The agent still
*returns* the response object — the only thing suppressed is the
in-flight streaming print.

This means when the orchestrator (eventually) calls eight
specialists, stdout stays clean. The orchestrator itself will need
a separate decision about whether *it* should stream — for dev
runs probably yes, for deployed runs probably no.

### Output-format markers carry the structure

In Phase 1, every research output was a Pydantic schema with named
fields and Literal enum constraints. In Phase 2, structure lives
in the prose response, marked by uppercase headers:

```
ITEM 1
Headline: ...
Source: ...
URL: ...
Why it matters: ...
Direction: supports_trend
Timeframe: short_term

ITEM 2
...
```

This is the text-native bet from STEP-03 in action. The marker
(`ITEM 1`, `EVENT 1`, `THEME 1`) is what downstream parsers will
look for; the field labels within each block are conventions for
the model to follow consistently.

Across seven smoke runs the model honoured the markers reliably.
Variations appeared in the prose *around* the markers (preambles,
occasional code fences, occasional duplication) — those are
detailed in observations.md — but the structural markers themselves
held.

### `NO EVENTS` as the empty-state convention

Phase 1 handled empty catalyst days by returning an empty events
list — a Pydantic-typed `CatalystResearch(events=[])`. In Phase 2
text-native there's no list to be empty. The convention I picked:
emit the literal string `NO EVENTS` when the day has no
oil-relevant scheduled releases.

This is a small text-native invention. It's not perfectly stable
yet — see the observations on interpretive variance — but the
basic shape (explicit marker for empty state, rather than just an
empty response) is what an orchestrator parser can detect cleanly.

### Build-period observations are worth capturing as they happen

After PR 1 I started `docs/observations.md` — a running log of
text-native behaviour observations, dated, with format
*"observed / what we did / why not more / implication."* PR 2
added three more entries.

The reason for the log: the text-native bet in STEP-03 said
"hybrid where quality forces it." Whether quality forces it is
an empirical question; the answers live in observations across
many specialist runs. Without a durable place to capture them,
the observations get stuck in chat transcripts and lost between
PRs.

After two PRs the log has six entries. Several are minor (preamble
drift, direction-call instability). One is structural (preamble
drift confirmed across 7/7 runs spanning three specialists). One
hints at a potential hybrid promotion trigger (the EVENT-block
duplication, which has parse-correctness implications).

Worth doing. Should keep happening for every subsequent specialist.

### Phase 1 prompt lessons port verbatim

Several Phase 1 prompt-engineering lessons land in Phase 2
unchanged because they're about Claude's behaviour, not the
framework:

- **"Use confidence honestly. Low is a valid and useful rating"**
  in geo — model uses `low` when warranted, including in the smoke
  runs. The permission-to-admit-uncertainty framing works.
- **"Distinct themes only"** in geo — model surfaces 3-5
  non-overlapping themes per run rather than repackaging the same
  story under different labels.
- **"Quality over quantity"** in news — model surfaces 4-5 items
  with real substance rather than padding to a higher count.
- **"Empty list is a valid response"** in catalysts — became
  `NO EVENTS` in text-native, same effect.

These all transferred without adjustment. STEP-03's claim that
prompt-level lessons port unchanged is holding up.

## What surprised me

- **How small the specialist template is.** Eight lines of Agent
  config and a one-paragraph description. The work is entirely in
  the markdown prompt. This shifts where prompt engineering
  matters — Phase 1 had it spread across nodes, helper functions,
  and state-flow logic; Phase 2 concentrates it in the markdown
  files. Diffs to a specialist's behaviour are diffs to its
  prompt.

- **The preamble drift is structural.** Across 7/7 smoke runs
  spanning three different research specialists, the model opened
  with "Based on my research..." or similar before the first
  structural marker, despite the system prompt explicitly saying
  "No preamble." This isn't a per-specialist quirk; it's how
  Bedrock-Claude responds to tool-equipped agents asked to produce
  structured prose. Plan for the parser to be lenient about
  leading content, not for the prompt to fix it.

- **The catalysts EVENT-block duplication.** One run produced its
  EVENT block twice — once in flowing prose, then again wrapped
  in a code fence. Same content, but a naive parser would see two
  events from one. Distinct from preamble drift in that it has
  parse-correctness implications, not just cosmetics. Logged with
  the implication that if it persists, it's the strongest signal
  yet for hybrid promotion.

- **catalysts day-to-day judgement is interpretive.** Same input,
  two runs on May 11 (a Monday with thin oil-specific catalysts),
  produced different decisions: one EVENT for US Existing Home
  Sales with `importance: low` in run 1, `NO EVENTS` in run 2.
  Both defensible. In Phase 1 this ambiguity was absorbed by the
  `importance` field; in text-native it lives in whether to emit
  an EVENT block at all. The orchestrator will need to handle
  both shapes equivalently.

## What's NOT decided yet

- **Whether the preamble drift forces parser leniency or prompt
  tightening or both.** Leaning parser leniency. Will revisit
  if more specialists show it (very likely) or if it interferes
  with orchestrator behaviour.
- **Whether the EVENT-block duplication forces hybrid promotion
  for `research_catalysts`.** Need more data. One occurrence
  isn't enough to act on; will watch in subsequent runs and in
  end-to-end orchestrator invocations.
- **Whether the catalysts empty-day variance forces tighter prompt
  guidance.** Defer until we see how the orchestrator consumes
  both shapes. If `NO EVENTS` and "all events are importance:
  low" route equivalently downstream, leave the prompt alone.
- **Streaming control for the orchestrator.** Specialists are
  silent via `callback_handler=None`. The orchestrator needs its
  own decision — visible reasoning during dev runs is useful,
  noise in production probably isn't.

## Open questions

- **Will the same prompt patterns work for synthesise, draft, and
  the auditors?** The research specialists all share a shape:
  search + reason + structured prose. Synthesise reads structured
  prose and produces interpretation; auditors read prose and
  return verdicts; renderers turn structure into final prose.
  Those are different shapes. The specialist template may need
  variations.
- **Does the orchestrator's input-assembly logic stay simple, or
  does it grow as specialists multiply?** Each downstream
  specialist takes a concatenation of upstream specialist outputs.
  The orchestrator's prompt encodes that assembly. With four
  research specialists feeding synthesise, the input string is
  already meaningful in size; with all eight specialists in play
  it may need explicit packaging.
- **Cost per smoke run.** Anecdotal so far. Each Tavily-bound
  specialist invocation uses 1-3 search calls plus Claude
  reasoning over the results. Worth measuring before we have an
  orchestrator that calls eight specialists per briefing.

## Glossary

- **Plain tool** — Python function decorated with Strands' `@tool`.
  No LLM. Used for deterministic operations like price fetching.
- **Specialist agent** — A Strands `Agent` configured for a single
  focused job (one prompt, optionally one or more bound tools).
  Returns text. Stateless across calls by default.
- **Specialist template** — The eight-line shape every Phase 2
  specialist takes: `name`, `description`, `system_prompt`,
  `model`, `tools`, `callback_handler=None`, wrapped in a factory
  function.
- **Structural marker** — Uppercase header in the specialist's
  prose response that downstream parsers detect (e.g. `ITEM 1`,
  `EVENT 1`, `THEME 1`, `NO EVENTS`). The text-native equivalent
  of Phase 1's Pydantic field names.
- **Preamble drift** — Observed pattern where research specialists
  open their response with a short narrative preamble before the
  first structural marker, despite the prompt saying "no preamble."
  Mild and parser-tolerable.
- **Block duplication** — Observed pattern (one occurrence so far)
  where a specialist emits the same structural block twice in one
  response (once inline, once in a code fence). Has parse-
  correctness implications.
