# STEP-04 — First nodes: Plan and Research Price

## What I did

- Wired the first two real nodes into the graph: `plan` and `research_price`.
- Implemented `plan` using `with_structured_output` against a `ResearchPlan`
  TypedDict — first time the LLM produces structured output rather than
  free text.
- Implemented `research_price` as a deterministic data fetch, no LLM. Used
  `yfinance` to pull WTI crude futures (`CL=F`) and computed a small set
  of derived metrics (intraday range, distance from moving averages,
  52-week bounds).
- Built `PriceDataSource` as a small class wrapping the yfinance call so
  the node stays clean and the data source is testable in isolation.
- Set up the `prompts/` directory with a `load_prompt` helper, and wrote
  `prompts/plan.md` as the first prompt template.
- Wrote contract tests for both nodes against real APIs (Anthropic for
  plan, yfinance for price). Tests are slow but high-fidelity.

## What I learned

### Two nodes, two completely different patterns

`plan` and `research_price` look like they should be similar — both are
"research" nodes in some sense, both write to state. But the right
implementation is wildly different. `plan` is an LLM call that produces
structured output. `research_price` is a function that fetches numbers.
No LLM. No prompt. No model.

This is the first concrete instance of a principle that runs through the
whole agent: **use the simplest tool that can do the job.** Price data
is deterministic and well-defined. Asking an LLM to "research the price
of crude oil" would be slower, more expensive, and less reliable than
calling yfinance and doing arithmetic.

The bigger lesson: not every node in an "agent" needs the agent stuff.
Some nodes are just functions. The graph framework doesn't care.

### `with_structured_output` is the workhorse

The `plan` node uses the simplest LLM-call pattern:

```python
model = ChatAnthropic(model="claude-haiku-4-5")
structured_model = model.with_structured_output(ResearchPlan)
response = structured_model.invoke([HumanMessage(content=prompt)])
```

Three lines, and the response is a typed dict matching the schema. No
JSON parsing, no validation, no try/except around malformed output.
LangChain handles the schema enforcement at the provider level — for
Anthropic, that means using their tool-use mechanism with the schema as
the tool's input shape.

This is the pattern that ends up everywhere in the project. The research
nodes use it (with web search bound on top); synthesise uses it; the
auditors use it; draft and deliver use it. The variations that matter
are which *tools* are bound to the model and what's in the prompt — the
structured-output mechanism itself is uniform.

### TypedDicts everywhere

The `ResearchPlan` is a `TypedDict`, not a Pydantic model:

```python
class ResearchPlan(TypedDict):
    price: str
    news: str
    catalysts: str
    geopolitics: str
```

I went into this expecting Pydantic because that's what most LangChain
tutorials show. But TypedDicts are fine — `with_structured_output`
accepts both, and TypedDicts have less ceremony. They're also what
LangGraph's State *has* to be in 1.0, so using TypedDicts everywhere
keeps the codebase consistent.

The minor downside: no runtime validation. If the LLM somehow produces
output that doesn't match the schema, you find out at field access time,
not at parse time. In practice this hasn't been an issue — the
structured-output mechanism is reliable enough that schema mismatches
are rare. When they do happen, they tend to happen in patterns that no
amount of validation would catch (see the `create_agent` flakiness
story in STEP-05).

### Data sources as classes, not free functions

The price fetch could have been a free function:

```python
def fetch_price(symbol: str) -> dict: ...
```

Instead I made it a class:

```python
class PriceDataSource:
    def fetch(self, symbol: str) -> PriceSnapshot: ...
```

This feels like over-engineering for one method. But it pays off
immediately when writing tests — the class is easy to mock, easy to
swap, easy to add caching to later. It also signals intent: this is a
*data source*, a category of thing the project will have several of
(prices, news, catalysts, etc.), and they should follow a consistent
shape.

For Phase 1, only prices are a "real" data source — the others are LLM
calls with web search. But making the structural choice now means
prices fits into a category rather than being a one-off function.

### Prompts as files, not strings

Prompts get long. Embedding them as multi-line Python strings makes
`nodes.py` unreadable. Instead I set up:

```
src/briefing_agent/prompts/
  __init__.py          # has load_prompt() helper
  plan.md              # the actual prompt
```

`load_prompt("plan", **kwargs)` reads the markdown file, runs
`str.format()` substitution against the kwargs, and returns the
resulting string. Each variable in the prompt is `{name}`; Python's
format string semantics handle the substitution.

The cost: any literal `{` or `}` in the prompt has to be escaped (`{{`
or `}}`). In practice I haven't needed to.

The benefit: prompts are first-class assets. They get their own files,
their own diff history, can be edited in markdown editors with proper
preview, and don't pollute the Python source.

### Real APIs in tests, accept the cost

The contract tests for `plan` and `research_price` both hit real APIs.
For `plan`, that's an Anthropic call (~$0.001 per test, ~5 seconds).
For `research_price`, that's a yfinance fetch (free but ~1 second).

I considered mocking. Decided not to. Reasons:

- The point of these tests is to verify the *contract* — that the
  function returns the shape the rest of the graph expects. A mock
  would just verify the mock.
- The cost is trivial at the volume we run tests (single-digit cents
  per full suite run).
- Real-API tests catch real failures — if yfinance changes their
  response shape, or if a model deprecation breaks structured output,
  the tests will fail loudly. With mocks, you'd ship a broken graph.

Long-term, if the test suite gets too slow to run on every commit, the
right answer is probably to mark integration tests separately and run
them less often. Not to mock.

## What surprised me

- How much of the LangGraph "agent shape" is just normal Python with one
  good abstraction (structured output). I expected more framework
  ceremony.

- That `with_structured_output` actually works first-time on simple
  schemas. Expected to spend hours debugging "the LLM keeps adding extra
  fields"; in practice the provider-level schema enforcement is rock
  solid for one-shot calls. (The flakiness story is specifically about
  agent loops with web search — that comes in STEP-05.)

- Writing prompts to files felt heavy at first. Worth it after the
  second prompt — the moment you have two long prompts in `nodes.py`
  is the moment you wish they weren't.

## Open questions

- Should `PriceDataSource` cache results? A briefing run hits price
  once; multiple runs in the same session would hit it multiple times.
  Probably premature.

- Is hardcoding `CL=F` defensible long-term? When the project supports
  multiple commodities, a `commodity → symbol` mapping needs to exist
  somewhere. For Phase 1, the constant is fine.

- Can I use `model.with_structured_output(...)` and `bind_tools(...)`
  in the same chain? The next step is news research, which needs both.

## Glossary

- **`with_structured_output`** — A method on LangChain `ChatModel`s that
  forces the response to match a given schema. Typed result, no JSON
  parsing.
- **`TypedDict`** — Python's typed-dict construct. Behaves like a dict
  at runtime but has type hints for keys. Used everywhere in this
  project for schemas and for the graph's State.
- **`load_prompt`** — Tiny helper in `prompts/__init__.py` that reads a
  markdown file by name and runs `str.format()` substitution against
  kwargs. Lets prompts live as `.md` files.
- **Contract test** — A test that verifies a function returns the shape
  its callers expect, without testing the internal implementation.
  Hits real APIs where applicable.
