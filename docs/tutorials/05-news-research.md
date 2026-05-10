# STEP-05 — Research: News (the agent loop)

## What I did

- Implemented `research_news` — first node that does *iterative* research,
  with web search and a structured output schema.
- Used `create_agent` with Anthropic's server-side `web_search_20250305`
  tool and a `NewsResearch` response format.
- Wrote the prompt to ask for 3-5 oil-related news items from the last 24
  hours, each with `direction` (supports/reverses trend, neutral) and
  `timeframe` (short_term, structural) as Literal-typed enum fields.
- Wrote three contract tests against the real Anthropic + web search
  combination.
- *Later, in STEP-12*: hit a known-fragile failure mode and migrated this
  node to the simpler `bind_tools + with_structured_output` pattern that
  catalysts and geo had been using all along.

## What I learned

### `create_agent` is the high-level loop

For a node where the model needs to make multiple decisions — search for
this, evaluate the result, refine the query, search again — `create_agent`
is the LangChain abstraction. You hand it a model, a list of tools, and
optionally a `response_format`. It returns a runnable that, when invoked,
runs the full reason-act-observe loop until the model decides it's done.

```python
agent = create_agent(
    model="anthropic:claude-haiku-4-5",
    tools=[web_search_tool],
    response_format=NewsResearch,
)
result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
return {"news_research": result["structured_response"]}
```

The `response_format` flag is what makes this useful for our case — it
forces the agent's final output to match the `NewsResearch` schema after
all the iteration is done.

### Anthropic web search is server-side, not a tool we run

The web search "tool" is a dict, not a function:

```python
web_search_tool = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5,
}
```

This isn't a Python tool we implement. It's an instruction to Anthropic's
API saying *the model can request web searches, which Anthropic's
infrastructure performs and returns to the model.* Our code never sees
the search happen — it's invisible from our side. The model gets results
back, reasons over them, possibly searches again, and eventually emits a
structured response.

The `max_uses: 5` cap is important. Without it, the agent can spiral into
"let me search for one more thing." Five was generous for news research;
catalysts and geo settled on lower caps later (3 and 4 respectively).

### `Literal` types beat string types for enum fields

First version of the schema had `direction: str`. The model produced
`"reverse"` instead of `"reverses_trend"` on one of the early test runs
and downstream code that expected exact matches broke.

Switched to `Literal["supports_trend", "reverses_trend", "neutral"]`. The
schema validator now enforces the exact values at the provider level —
the model literally cannot produce a string outside the set. Free
correctness, no validation code.

This became a pattern for every enum-shaped field in the project:
direction, timeframe, importance, confidence, impact_direction. Any time
the schema has "one of these N options," `Literal` is the right type.

### The news prompt does some real editorial work

The prompt asks for items that *matter for the briefing*, not just any
news. It instructs the model to skip duplicate stories, prefer original
sources over aggregators, and assign each item a direction and timeframe
based on its likely effect on price.

The interesting design choice: I let the model decide what's worth
including. The schema says "list of items" without a fixed count, with
guidance for 3-5. In practice the model returns 4-5 items consistently;
I haven't seen it return one or ten. The prompt's phrasing acts as a
soft constraint that the model honours.

### `create_agent` + Anthropic server-side tools + `response_format` is fragile

This is the part of the story I have to be honest about, because it ate
a lot of debugging time later in the project.

The pattern *works*. Most of the time. The failure mode is specific:
when the model is satisfied it has enough information, it produces the
JSON for the schema — and then sometimes *keeps generating*. A closing
sentence, a summary, a caveat. The structured-output parser sees valid
JSON followed by extra content, throws `JSONDecodeError: Extra data`,
and the whole call fails.

I shipped news with this pattern. The tests passed. I went on to
catalysts, hit the same failure mode there during initial development,
and migrated catalysts to a simpler pattern. *I left news on
`create_agent` because it was passing.*

In STEP-12, during the deliver PR, news finally produced the failure mode
in a test run. The fix took about 10 lines: same migration as catalysts,
moving to `ChatAnthropic(...).bind_tools([...]).with_structured_output(...)`.
News doesn't actually need the iterative loop — for "find me 4-5 recent
oil news items," one search-and-respond cycle is plenty.

### Lesson: `create_agent` is genuinely overkill for most research

Looking back: of the four research nodes, only news had a *plausible*
case for needing iterative search. Catalysts is "what scheduled events
are today?" — a bounded lookup. Geopolitics is "what are the structural
themes?" — another bounded lookup. Even news, in practice, is "find a
handful of recent items" — also bounded.

If I were starting over, I'd default to `bind_tools +
with_structured_output` for all research nodes and only reach for
`create_agent` if I had concrete evidence that one search wasn't enough.
The simpler pattern is more reliable, faster, and uses fewer tokens. The
"agent" part of "agent loop" has to be earned by the task.

## What surprised me

- That a tool description as a *dict* counts as binding a tool. I expected
  Python callable. It's the LangChain-ism that makes provider-side tools
  fit the same interface as user-side tools.

- How clean the `Literal` upgrade felt. Five characters of type and the
  whole class of "model produced 'reverse' instead of 'reverses_trend'"
  bugs evaporates.

- That the `create_agent` failure mode is *probabilistic*. It doesn't
  fail every time. It fails when the model is in a particular mood about
  closing commentary. This makes it especially nasty — passes in tests
  for weeks, fails in production.

## Open questions

- Why does Anthropic's API allow extra content after a JSON response when
  `response_format` is set? Feels like a bug. (Possibly fixed by now;
  I haven't checked.)

- Is there a clean way to retry on `StructuredOutputValidationError` from
  inside `create_agent`? Adding retry-with-tighter-prompt logic at the
  node level felt heavier than just switching patterns.

- Can `bind_tools` handle multiple tool calls in a single invocation, or
  only one? The catalysts node uses it with one search call and that
  works fine; haven't tested with multiple.

## Glossary

- **`create_agent`** — LangChain's high-level wrapper for tool-using
  agents. Runs a reason-act loop until the model decides it's done.
  Optional `response_format` forces the final output to a schema.
- **Server-side tool** — A tool the LLM provider runs themselves
  (Anthropic web search, code execution). Defined as a dict, not a
  Python callable. Our code never sees the call happen.
- **Agent loop** — The reason → act → observe cycle. The model produces
  a tool call, the tool runs, the result goes back to the model, the
  model reasons over it and either calls another tool or produces final
  output.
- **`Literal` type** — Python's typed-enum alternative. `Literal["a",
  "b", "c"]` means "one of these three exact strings." Enforced at
  schema-validation level when used in TypedDicts.
