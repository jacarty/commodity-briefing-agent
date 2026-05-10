# STEP-06 — Bounded research: Catalysts and Geopolitics

## What I did

- Implemented `research_catalysts` and `research_geo` together — same
  pattern, different schemas and prompts.
- Used `bind_tools + with_structured_output` instead of `create_agent`.
  Single search-and-respond cycle, no agent loop.
- Defined richer schemas with multiple `Literal`-typed enum fields:
  catalysts gets `importance` (high/medium/low); geo gets
  `impact_direction` (bullish/bearish/ambiguous), `timeframe`
  (near_term/medium_term/long_term), and `confidence` (high/medium/low).
- During catalysts development, hit the `create_agent` failure mode
  predicted in STEP-05. Pivoted to the simpler pattern. Kept `bind_tools
  + with_structured_output` for geo from the start.

## What I learned

### `bind_tools + with_structured_output` is the cleaner pattern

```python
model = (
    ChatAnthropic(model="claude-haiku-4-5")
    .bind_tools([web_search_tool])
    .with_structured_output(CatalystResearch)
)
result = model.invoke([HumanMessage(content=prompt)])
```

One round trip. The model gets the prompt, decides whether to search,
performs zero-or-more searches via the bound tool, and emits the
structured response. No agent loop, no iteration. For research that
fits in one go — and almost all of it does — this is enough.

The trade-off vs `create_agent`: you lose the ability to iterate. If
the first search comes back unhelpful, the model can't refine and try
again. For catalysts ("what scheduled events are today?") and geo
("what are the structural themes?"), this isn't a real loss. The model
plans its query well enough on the first attempt that one cycle
suffices.

### Schema design carries editorial weight

Geo has three enum fields, not one. That's deliberate.

- `impact_direction` says whether the theme pushes price up, down, or
  neither
- `timeframe` says when the impact lands
- `confidence` says how sure the model is of its assessment

Each captures a different axis. Without `confidence`, the synthesise
node downstream can't distinguish "Hormuz blockade" (we know this is
happening, with measurable impact) from "China demand might soften"
(plausible but uncertain). With it, synthesise can weight high-
confidence themes and hedge on low-confidence ones — and the auditor
can later check that the weighting is honest.

The lesson: the schema isn't just a data structure, it's a thinking
tool. Designing the schema is designing how downstream nodes can
reason about the output.

### Confidence ratings need permission to be low

The geo prompt explicitly endorses "low" as a valid rating: *"low is a
valid and useful rating — geopolitics is genuinely uncertain."*

Without that, models default to "medium" or "high" because they sound
authoritative. The prompt gives explicit permission to admit uncertainty,
and in practice the model uses `low` when it should — which is the
behaviour I want.

This is broader than confidence ratings. Anywhere the prompt asks the
model for a calibrated judgement, naming the underweighted answer as
valid pushes against the model's instinct to over-claim.

### "Distinct themes only" prevents repetition

First version of the geo prompt asked for ~5 structural themes. The
model returned five themes that were really one story: "Iran tensions,"
"Hormuz risk," "Saudi-Iran proxy," "Yemen Houthi disruption," "Persian
Gulf shipping." All causally linked, all variations on Middle East
chokepoint risk.

Added an explicit instruction: *"distinct themes only — pick the more
fundamental and reference others within its summary."* Output now
includes Hormuz as one theme and OPEC+ discipline as another, which is
the right level of granularity.

Anti-repetition instructions like this come up again in draft (don't
re-cover the same story across sections) and synthesise (don't restate
the dominant narrative in every field). It's a recurring need.

### The catalysts pivot earned the pattern

I started catalysts on `create_agent` to match news. Hit `JSONDecodeError:
Extra data` repeatedly. The model would emit the schema JSON and then
keep generating commentary about the search.

Switched to `bind_tools + with_structured_output`. Failure went away.
This was the moment the pattern cemented for the rest of the project —
geo was built directly on it, and news was eventually migrated to it
(STEP-12 closeout).

The principle: if the task is "search once, respond with structure,"
don't reach for an agent loop. The simpler pattern is more reliable for
this shape of work.

## What surprised me

- That two enum fields plus one open-ended `theme` string captures the
  shape of geopolitical analysis well. I expected to need more
  structure. I didn't.

- How much the prompt wording about "what is NOT a theme" mattered. The
  negative space defines the positive space.

- That `bind_tools + with_structured_output` produces well-grounded
  output even with `max_uses: 3`. I expected richer research with more
  searches; in practice, three good searches beat five mediocre ones.

## Open questions

- Could a single shared "research base class" abstract the
  `bind_tools + with_structured_output` pattern? The three research
  nodes have a lot of structural similarity. Probably not worth it —
  the differences (max_uses, schema, prompt) live in the parts that
  matter, and the duplication is mostly boilerplate.

- Is `max_uses` overspecified? Could let the model decide.

## Glossary

- **`bind_tools`** — Returns a model with tools available. The model
  can call them during a single invocation. Distinct from
  `create_agent`, which manages an iterative loop over the bindings.
- **Single-shot research** — One model invocation that may include
  tool calls but produces one final structured response. Cheaper and
  more reliable than iterative agent loops for bounded research tasks.
- **Calibration** — How well a confidence rating matches the actual
  certainty of the underlying fact. Calibrated outputs distinguish
  what we know from what we suspect.
