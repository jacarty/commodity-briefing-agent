# STEP-03 — Design

The architectural design for Phase 3. Same conceptual agent as
Phase 1 and Phase 2 (research → synthesise → audit → draft →
audit → deliver), built idiomatically on ADK with Gemini 2.5
Flash, with workflow agents handling the structure that Phase 2
encoded in prose.

This is the design step. No code in this doc — code starts in PR
1. The point is to settle architecture, state shape, and build
sequencing before any specialist lands.

## What I did

Read the ADK docs on multi-agent systems, workflow agents
(`SequentialAgent`, `LoopAgent`, `ParallelAgent`), custom agents
(`BaseAgent` subclassing), and structured output (`output_schema`
with Pydantic). Identified one significant architectural
constraint (the LoopAgent escalation problem). Translated the
Phase 1/Phase 2 agent design into ADK primitives.

## Architecture overview

```
PhaseThreeOrchestrator (custom BaseAgent)
├── ParallelAgent: research_news + research_catalysts + research_geo
├── fetch_price (FunctionTool, called directly by orchestrator)
├── LoopAgent #1 (max_iterations=2):
│       synthesise → cross_check → exit_or_continue
├── LoopAgent #2 (max_iterations=2):
│       draft → sense_check → exit_or_revise
└── FinalBrief assembly (output_schema=FinalBrief)
```

Eight specialists same as Phase 2. One `fetch_price` function
tool. Two retry loops with hard caps. Custom top-level
orchestrator. FinalBrief as Pydantic-typed structured output at
the boundary.

## The LoopAgent escalation gotcha (and why we use a custom orchestrator)

The single most important architectural fact about Phase 3 is a
limitation in ADK's `LoopAgent`. When a sub-agent inside a
`LoopAgent` exits by setting `tool_context.actions.escalate =
True`, the escalation signal propagates *up* — it stops the loop
AND its parent `SequentialAgent`, halting any subsequent steps
in the sequence.

This is documented behaviour, not a bug. It means a naive
implementation like this is broken:

```python
# Conceptually broken: when LoopAgent 1 exits via escalate,
# LoopAgent 2 never runs because the SequentialAgent halts too.
root = SequentialAgent(sub_agents=[
    research_parallel,
    LoopAgent(sub_agents=[synthesise, cross_check_with_exit], max_iterations=2),
    LoopAgent(sub_agents=[draft, sense_check_with_exit], max_iterations=2),
    final_assembly,
])
```

The community-recommended workaround is to write a custom
`BaseAgent` subclass that orchestrates the workflow with
explicit Python `async`/`await` and yields events. ADK supports
this as a first-class pattern — `BaseAgent` is the foundational
primitive that workflow agents inherit from.

So our `PhaseThreeOrchestrator` is a custom `BaseAgent` that:

1. Runs `ParallelAgent(research_news, research_catalysts, research_geo)` via `run_async`
2. Calls `fetch_price` directly as a function (no LLM involved)
3. Runs the synthesis `LoopAgent`, consumes its events, ignores
   the escalate signal that would otherwise halt the sequence
4. Runs the rendering `LoopAgent`, same pattern
5. Calls the FinalBrief assembly agent to produce structured
   output

This is the truly idiomatic ADK pattern for our use case.

## State design

ADK uses `session.state` as the inter-agent data carrier. Each
`LlmAgent` can specify an `output_key`, which writes its final
response to `state[output_key]`. Subsequent agents read from
state via template substitution in their instructions: `{key}`
in an instruction string is replaced with `state[key]` at
invocation time.

State keys, in order of when they're written:

| Key | Written by | Shape |
|---|---|---|
| `price_data` | orchestrator after `fetch_price` | dict (price snapshot) |
| `news_research` | `research_news` | str (5 NEWS ITEMs in prose) |
| `catalysts_research` | `research_catalysts` | str (EVENTs in prose) |
| `geo_research` | `research_geo` | str (5 GEOPOLITICAL THEMEs in prose) |
| `synthesis` | `synthesise` (rewritten each loop) | str (5-section synthesis) |
| `cross_check_result` | `cross_check` (rewritten each loop) | str (VERDICT + issues) |
| `draft` | `draft` (written once) | str (4-section brief) |
| `sense_check_result` | `sense_check` (rewritten each loop) | str (VERDICT + revision notes) |
| `revised_draft` | `revise` (rewritten each loop iteration) | str (revised 4-section brief) |
| `final_brief` | final assembly | FinalBrief (Pydantic) |

A few notes on this design:

- **Prose-typed for research outputs**, same as Phase 2. The
  section headers (`ITEM 1`, `EVENT 1`, etc.) carry the structure.
- **Synthesis and audit outputs are re-written each loop
  iteration** — Phase 1's discipline applied here.
- **`revised_draft` overwrites `draft`** semantically — after the
  first revision, `revised_draft` becomes the canonical draft for
  any subsequent sense_check iteration.
- **`final_brief` is the only typed slot** — Pydantic enforced
  via `output_schema=FinalBrief` on the assembly agent.

## Agent definitions

### Research specialists (3 × `LlmAgent`, each in the `ParallelAgent`)

Same prompts as Phase 2 (port verbatim — they're about Claude /
Gemini editorial discipline, not framework specifics). Each
agent:

- `model="gemini-2.5-flash"`
- `tools=[google_search]` — first-party search, replaces Tavily
- `output_key="news_research"` (or catalysts / geo)
- `instruction=` Phase 2 prompt with `{commodity}` and
  `{target_date}` substituted via state

The `ParallelAgent` runs them concurrently in isolated branches.
Each writes to its own `output_key` — no race conditions because
the keys are distinct.

### `fetch_price` (FunctionTool, no LLM)

Same as Phase 2 — a yfinance-backed function that returns a
price snapshot for `CL=F`. In Phase 3 the custom orchestrator
calls it directly:

```python
price = fetch_price()
ctx.session.state["price_data"] = price
```

No LLM wrapper. Deterministic data, no reason for an agent layer.

### `synthesise` (`LlmAgent`)

- Reads `{price_data}`, `{news_research}`, `{catalysts_research}`,
  `{geo_research}` from state via instruction template substitution
- Writes to `state["synthesis"]`
- Same prompt as Phase 2 — five mandatory sections (DOMINANT
  NARRATIVE, PRICE INTERPRETATION, CROSS-STREAM SIGNALS, RISKS
  TO VIEW, HEADLINE METRICS)
- No tools, no `output_schema` — prose output, structure via prompt

### `cross_check` (`LlmAgent` with `exit_loop` tool)

- Reads `{synthesis}`, `{news_research}`, `{catalysts_research}`,
  `{geo_research}` from state
- Writes to `state["cross_check_result"]`
- Same prompt as Phase 2 — VERDICT: PASS / FAIL opening, issues
  categorised
- **Has access to an `exit_loop` function tool** that sets
  `tool_context.actions.escalate = True`
- Prompt says: "If VERDICT is PASS, call `exit_loop()` to signal
  the synthesis is good. Otherwise, output your full
  VERDICT/issues/RE-RESEARCH TARGETS response and the loop will
  re-run the synthesis."

This is the ADK-idiomatic equivalent of Phase 2's "VERDICT: PASS
on the first line is the routing signal." Phase 2's signal was
text the orchestrator parsed; Phase 3's signal is a function
call the framework interprets.

### `draft` (`LlmAgent`)

- Reads `{synthesis}` from state
- Writes to `state["draft"]`
- Same prompt as Phase 2 — four mandatory section headers (PRICE
  SECTION, NEWS SECTION, CATALYSTS SECTION, GEOPOLITICS SECTION)
- No tools, no `output_schema`

### `sense_check` (`LlmAgent` with `exit_loop` tool)

- Reads `{synthesis}` and the current draft (`{draft}` initially,
  `{revised_draft}` after first revision)
- Writes to `state["sense_check_result"]`
- Same VERDICT pattern as cross_check
- Has access to `exit_loop` tool

The "which draft do I check" question is handled in the prompt:
the agent's instruction will be conditional on which keys exist
in state. Cleaner alternative: always check `state["draft"]`
where `revise` writes back to that same key. We'll use the
cleaner version — `revise` overwrites `state["draft"]`.

### `revise` (`LlmAgent`)

- Reads `{synthesis}`, `{draft}`, `{sense_check_result}` from state
- Writes back to `state["draft"]` (overwrites)
- Same prompt as Phase 2 — bolded "targeted revision, not a
  rewrite" instruction

### FinalBrief assembly (`LlmAgent` with `output_schema`)

- Reads `{draft}` from state (the latest version, post-revision)
- Outputs a `FinalBrief` Pydantic instance
- `output_schema=FinalBrief`
- ADK's `_OutputSchemaRequestProcessor` enforces Pydantic
  validation natively for Gemini 2.0+ via Vertex AI

`FinalBrief` ports unchanged from Phase 2:

```python
class FinalBrief(BaseModel):
    subject: str       # e.g. "Crude oil briefing — 2026-05-12"
    html_body: str     # HTML-rendered brief
    plain_text_body: str  # Plain-text rendered brief
```

## Workflow agent wiring

```python
# Two retry loops as workflow agents

synthesis_loop = LoopAgent(
    name="synthesis_loop",
    sub_agents=[synthesise, cross_check],
    max_iterations=2,
)

rendering_loop = LoopAgent(
    name="rendering_loop",
    sub_agents=[draft_or_revise_decision, sense_check],
    max_iterations=2,
)
```

The `draft_or_revise_decision` is a small helper agent that picks
between `draft` (first iteration) and `revise` (subsequent
iterations). Could be a custom `BaseAgent` or just two agents
where the prompt does the right thing based on state. Decided in
PR 4 when we build the rendering layer.

## Custom orchestrator

```python
class PhaseThreeOrchestrator(BaseAgent):
    """Top-level orchestrator. Coordinates research, synthesis,
    rendering, and final assembly. Custom BaseAgent because pure
    SequentialAgent doesn't handle LoopAgent escalation correctly.
    """

    async def _run_async_impl(self, ctx):
        # 1. Parallel research
        async for event in self.research_parallel.run_async(ctx):
            yield event

        # 2. Price snapshot
        ctx.session.state["price_data"] = fetch_price()

        # 3. Synthesis loop (with cap-fallback)
        async for event in self.synthesis_loop.run_async(ctx):
            # Strip escalate so the SequentialAgent equivalent
            # doesn't halt; the loop has already exited.
            event.actions.escalate = False
            yield event

        # 4. Rendering loop (same cap-fallback)
        async for event in self.rendering_loop.run_async(ctx):
            event.actions.escalate = False
            yield event

        # 5. Final brief assembly
        async for event in self.final_brief_agent.run_async(ctx):
            yield event
```

The `event.actions.escalate = False` line is the workaround for
the LoopAgent halt issue. Loops still exit early when their
sub-agents escalate; the orchestrator just doesn't propagate the
signal upward.

## The lessons from Phase 1 and Phase 2

| From | Lesson | How it lands in Phase 3 |
|---|---|---|
| Phase 1 | State-first design with typed schema | `session.state` keys defined upfront in this doc |
| Phase 1 | Bounded loops with explicit caps and safety-valve | `LoopAgent` with `max_iterations=2` for both retry loops |
| Phase 1 | Schema-as-contract via `with_structured_output` | `output_schema=FinalBrief` on the final assembly |
| Phase 2 | Pass-bias auditor prompts produce calibrated audits | cross_check and sense_check use the same prompts |
| Phase 2 | Editorial discipline lives in prompts | All specialist prompts port verbatim |
| Phase 2 | Custom orchestrator beats pure workflow when control flow gets non-trivial | `PhaseThreeOrchestrator(BaseAgent)` instead of pure `SequentialAgent` |
| Phase 2 | Text-native data flow works | Research outputs stay as prose with section-header conventions |
| Phase 2 | Validate then pin | Phase 3 already pinned at STEP-02 close |
| Phase 2 | Smoke-test design needs in-run side-by-side comparison | Carry the `difflib.SequenceMatcher` pattern forward for revise testing |

## What's NOT in Phase 3

Things ADK offers that we're deliberately not using:

- **Sessions / Memory Bank** — agent is one-shot daily, no
  conversation history or long-term memory needed
- **Example Store** — few-shot retrieval, not needed for our
  workflow
- **Code Execution sandbox** — agents don't need to run code
- **Agent Studio** — visual builder, not for our code-first project
- **Agent Gateway / Agent Identity / IAM policies** —
  production-scale governance, overkill for solo development
- **A2A (Agent-to-Agent) protocol** — relevant when agents talk
  to other organisations' agents; ours don't
- **`adk run` / `adk web`** — dev CLIs, see STEP-02 for why we
  invoke programmatically

Per the Phase 2 retrospective: "use what makes the agent better;
say no to the rest."

## Smoke testing strategy

Same shape as Phase 2:

- **Per-specialist smoke tests** for the four research-layer
  agents and the four analysis-layer agents
- **Dual-scenario smoke tests for auditors** (pass + fabricated-
  fail), reusing the fabrication-injection pattern from Phase 2
- **Chained smoke tests** for the synthesis and rendering loops
- **End-to-end orchestrator smoke** (happy path)
- **Failure-path orchestrator smokes** for both retry loops,
  with stubbed auditors that always escalate=False

All smoke tests use `asyncio.run()` and `Runner` +
`InMemorySessionService` (the pattern verified in STEP-02).

Cost tracking deferred per agreement.

## Build sequencing (PR plan)

Six PRs covering the build, with a deployment PR at the end:

| PR | Scope | Validates |
|---|---|---|
| PR 1 | `fetch_price`, `research_news`, prompt-loading helper, first smoke test | google_search-driven research works; prompt-port pattern works |
| PR 2 | `research_catalysts`, `research_geo`, `ParallelAgent` wrapper, parallel-research smoke | parallel execution works; all 3 research streams produce expected output |
| PR 3 | `synthesise`, `cross_check`, synthesis `LoopAgent`, dual-scenario auditor smoke | synthesis works; exit_loop pattern works for auditor; LoopAgent escalates correctly |
| PR 4 | `draft`, `sense_check`, `revise`, rendering `LoopAgent` | rendering layer works; revise stays targeted |
| PR 5 | `FinalBrief` model, `PhaseThreeOrchestrator`, happy + failure smokes, STEP-07 retrospective | full pipeline works; retry caps hold under failure; orchestrator manages escalate suppression correctly |
| PR 6 | Agent Engine deployment | Deploy works; agent runs on managed runtime |

Each PR ends with the same close-out as Phase 2: STEP doc,
observations entries, PR notes.

## Open questions for the build

These are real uncertainties that will be answered as PRs land:

- **Does `google_search` produce research output as rich as
  Tavily's?** Initial signal from STEP-02 was positive but a
  single-query test isn't conclusive. Will know after PR 1.
- **Does the prompt-port-verbatim hypothesis hold for Gemini
  Flash?** We're betting it does (the Phase 2 retrospective said
  "prompt-level discipline is the portable layer"). PR 1+ tests it.
- **Does `exit_loop` reliably exit the LoopAgent in our actual
  use case?** Two GitHub issues (#2988, #1100) report cases
  where escalation didn't take effect cleanly. PR 3 will tell us
  whether we hit this.
- **Does the `event.actions.escalate = False` suppression
  actually work?** It's a documented workaround but not deeply
  battle-tested. PR 5 with the full orchestrator validates this.
- **Will Gemini Flash do PASS-with-notes calibration as well as
  Haiku did?** Phase 2's auditor calibration depended on the
  model handling subtle distinctions. PR 3 (cross_check) is the
  first test.
- **Is `output_schema=FinalBrief` reliable enough for production
  use, or do we need retry logic around validation failures?**
  The ADK community has reported `pydantic.ValidationError` on
  malformed model outputs. PR 5 validates this.

## What I'm not yet sure about

The "draft vs revise" routing inside the rendering loop is the
fiddliest bit of the design. Two options:

- **(a)** A small custom `BaseAgent` that picks between
  `draft` and `revise` based on whether `state["draft"]` exists
- **(b)** Two separate `LlmAgent`s whose prompts include "if X,
  output Y, otherwise pass through"
- **(c)** Have `revise` always be the body of the loop, and seed
  `state["draft"]` from a one-time draft call *before* the loop
  starts

(c) is cleanest — the loop is just `revise + sense_check`, with
the initial draft created once before entering the loop. Phase 1's
design used something similar. **Going with (c)** unless PR 4
reveals a problem.

## Glossary

- **`BaseAgent`** — Foundational ADK agent class. Workflow
  agents and `LlmAgent` all inherit from it. Used directly when
  custom control flow is needed.
- **`LlmAgent`** — Standard agent type with an LLM backing.
  Configured with model, instruction, tools, optional
  `output_key` (writes final response to `session.state`), and
  optional `output_schema` (Pydantic-typed output).
- **`SequentialAgent`** — Workflow agent that runs sub-agents in
  fixed order. Each sub-agent's output becomes available to the
  next via state.
- **`LoopAgent`** — Workflow agent that iterates over sub-agents
  until `max_iterations` is hit OR a sub-agent escalates. Our
  retry-loop primitive.
- **`ParallelAgent`** — Workflow agent that runs sub-agents
  concurrently in isolated branches. Used for the 3-stream
  parallel research.
- **`output_key`** — String key under which an `LlmAgent` writes
  its final response into `session.state`. ADK's equivalent of
  Phase 1's typed state field assignment.
- **`output_schema`** — Pydantic `BaseModel` subclass that
  enforces the agent's final response structure. ADK validates
  with `model_validate_json`; raises `pydantic.ValidationError`
  if the model produces invalid output.
- **`exit_loop` / `escalate`** — Mechanism by which a sub-agent
  signals its parent loop to exit. A function tool sets
  `tool_context.actions.escalate = True`; the `LoopAgent` sees
  this on the yielded event and stops iterating.
- **`session.state` template substitution** — When an
  `LlmAgent`'s instruction contains `{key}`, ADK substitutes
  `session.state[key]` at invocation time. The equivalent of
  Phase 1's TypedDict access and Phase 2's prompt-string
  concatenation.
