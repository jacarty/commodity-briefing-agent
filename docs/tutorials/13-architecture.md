# STEP-13 — Architecture: lessons across the agent

## What I did

This isn't a new feature step. It's the architecture write-up — the
patterns that crystallised across the previous nine steps and the
view from the top of the agent.

After the deliver merge (STEP-12), the cleanup chore (Ruff +
pre-commit), and these tutorial files, Phase 1 is closed. This is
the place to step back and notice what the project taught me about
LangGraph and about agent design generally.

## What I learned

### State design is the whole game

The single most consequential thing I did in Phase 1 was design the
State schema in STEP-03 *before writing any nodes.* 18 fields, each
with a clear writer and clear readers, with the operational/audit
distinction explicit.

Because state was right, every subsequent node was small. Each node
just reads what it needs and writes what it owns. The hard work of
"how does this node communicate with that one" is absorbed by the
schema.

If state had been ad-hoc, every node would have grown its own
parameter-passing hacks and the graph would have become unreadable
within four or five nodes. I've seen this in older codebases. The
pattern of "design state first, build outward" is the prevention.

### Schema-as-contract is more powerful than I expected

Every LLM call in the project uses `with_structured_output` against
a TypedDict. Every research output, every audit result, every
rendered brief is schema-typed at the provider level.

The downstream effects:

- Nodes that consume other nodes' output don't need defensive parsing
- Schema mismatches fail at structured-output time, not at field
  access
- The schema *is* the documentation of what each node produces
- Schema design is a thinking tool — designing the synthesis schema
  forced me to articulate what synthesis was actually doing

I went into the project expecting to spend significant time on JSON
parsing, output validation, and "the model didn't return what I
asked for" debugging. Almost none of that work materialised. The
provider-level structured-output mechanism is rock-solid for one-shot
calls (the agent-loop edge case in STEP-05 notwithstanding).

### `with_structured_output` is the workhorse; agent loops are the exception

Twelve nodes. Eleven use simple LLM patterns: `with_structured_output`
alone or `bind_tools + with_structured_output`. One node (originally
news) used `create_agent`, and that one was eventually migrated.

The pattern that crystallised: default to the simpler patterns. Reach
for `create_agent` only when the task genuinely needs iterative
reason-act-observe cycles. Most "research" tasks don't.

This inverts the LangChain ecosystem's framing, which leads with
`create_agent` in nearly every quickstart. For most agent-shaped
work, the simpler patterns are more reliable, faster, and use fewer
tokens. The agent loop has to earn its place.

### Bounded loops, every time

Two feedback loops in this graph: cross-check / re-research and
sense-check / revise. Both are bounded by retry caps (2 attempts),
both have safety-valve routes that proceed even when the cap is hit.

If the cap fires, the brief still ships. The audit findings are
preserved in state for downstream awareness (sense-check produces a
summary even when failing; deliver could surface this if needed).

The principle: never trust an LLM-driven feedback loop to terminate
on its own. Bound it explicitly.

### Auditors need pass-bias prompts

Cross-check and sense-check both default to over-flagging without
explicit pass-bias instructions. The first version of cross-check
failed every synthesis on first pass — finding "issues" that were
really interpretive disagreements.

The fix is structural: name what is *not* a cross-check issue. List
specific examples. Set the bar at "would a competent reader reach a
wrong conclusion?" rather than "could this be phrased better?"

After tightening, the auditors mostly pass legitimate work and
mostly fail real fabrications. The ratio matters — auditor that
fails everything becomes noise; auditor that passes everything
becomes ceremony.

### Two-stage analyse-then-render

The architecture splits the analytical work (synthesise) from the
rendering (draft). Each stage has its own auditor (cross-check,
sense-check) operating at the right level.

Synthesise is structured-input → structured-output. Reasons over
research data, produces a structured analytical view. Cross-check
audits this against the underlying research.

Draft is structured-input → prose-output. Renders synthesis into
the briefing format. Sense-check audits the prose against the
synthesis it was meant to render.

The separation makes each stage tractable. Combining them into a
single "research-to-prose" node would have made auditing harder,
prompts longer, and failures harder to localise.

### Coach-first, code-second held throughout

Every step started with design discussion before code. Schemas were
agreed before implementation, prompts were drafted before nodes,
loops were diagrammed before edges were wired. This turned out to be
much faster than diving into code, because the conceptual mistakes
got caught at the design stage where they're cheap to fix.

The two times I deviated from this — the news flakiness migration
deferred for too long, and the cleanup chore deferred until PR 12 —
were the two times I had to pay the deferred cost.

### Phase 1 is genuinely complete

Twelve nodes, two bounded loops, schemas typed throughout, prompts
externalised as `.md` files, 35 tests against real APIs, full
end-to-end producing email-shaped output, linter and CI in place.

The architecture below is the result. The diagram is the same as
STEP-03's design — what's notable is that the design held. No major
refactors. No nodes deleted or re-purposed. The state schema added
exactly one field (`research_feedback`) beyond the original 18, and
that addition was anticipated structurally if not explicitly.

```mermaid
flowchart TD
    START([Start]) --> Plan[Plan]

    Plan --> ResPrice[Research: Price]
    Plan --> ResNews[Research: News]
    Plan --> ResCatalysts[Research: Catalysts]
    Plan --> ResGeo[Research: Geopolitics]

    ResPrice --> Synthesise[Synthesise]
    ResNews --> Synthesise
    ResCatalysts --> Synthesise
    ResGeo --> Synthesise

    Synthesise --> CrossCheck{Cross-check}

    CrossCheck -->|Issues found| ReResearch[Re-research]
    ReResearch --> Synthesise

    CrossCheck -->|Looks good| Draft[Draft]

    Draft --> SenseCheck{Sense-check}

    SenseCheck -->|Issues found| Revise[Revise]
    Revise --> SenseCheck

    SenseCheck -->|Looks good| Deliver[Deliver]

    Deliver --> END([End])
```

## What surprised me

- How well the upfront design held. I expected to discover the topology
  was wrong somewhere mid-project and need to refactor. The design
  was right enough to ship through.

- That nine of twelve nodes use the same handful of LangChain patterns.
  The variations live in prompts and schemas, not in framework usage.
  This is a healthy sign — the framework absorbs the orchestration so
  the work can be in the content.

- That the agent visibly self-corrects on real runs. The cross-check
  + re-research loop catches genuine fabrications and forces grounded
  output. This isn't theoretical agent behaviour; it's observable in
  test runs.

## Open questions

- The test suite hits real APIs every run. Currently fine; eventually
  some integration/unit split will help. The boundary is not yet
  clear.

- Several nodes instantiate `ChatAnthropic` per call. Wasteful but
  premature to refactor. A `model_factory` returning a configured
  client would be the right abstraction if perf ever matters.

- `briefing_spec` is supplied as an input dict but currently has only
  the four-section structure. As more commodities or formats arrive,
  it'll grow. The shape is right; the content is minimal.

## Glossary

- **State-first design** — Designing the graph's state schema before
  writing nodes. Forces clarity about what each node produces and
  consumes.
- **Schema-as-contract** — Using TypedDicts (or Pydantic) as the
  agreed shape for inter-node communication, enforced at the
  provider level via structured output.
- **Two-stage analyse-then-render** — Architectural split between
  the analytical work (producing structured interpretation) and the
  rendering work (producing prose from structured interpretation).
- **Bounded loop** — A feedback loop with an explicit retry cap and
  a safety-valve route that proceeds even when the cap fires. The
  alternative is infinite loops on edge cases.
